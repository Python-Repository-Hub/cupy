# import pytest
import unittest

import numpy

import cupy
from cupy import testing
from cupy.cuda import runtime
from cupy.cuda.texture import (ChannelFormatDescriptor, CUDAarray,
                               ResourceDescriptor, TextureDescriptor,
                               TextureObject)


stream_for_async_cpy = cupy.cuda.Stream()
dev = cupy.cuda.Device(runtime.getDevice())


@testing.gpu
@testing.parameterize(*testing.product({
    'xp': ('numpy', 'cupy'),
    'stream': (True, False),
    'dimensions': ((67, 0, 0), (67, 19, 0), (67, 19, 31)),
    'n_channels': (1, 2, 4),
    'dtype': (numpy.float16, numpy.float32, numpy.int8, numpy.int16,
              numpy.int32, numpy.uint8, numpy.uint16, numpy.uint32),
}))
class TestCUDAarray(unittest.TestCase):
    def test_array_gen_cpy(self):
        xp = numpy if self.xp == 'numpy' else cupy
        stream = None if not self.stream else stream_for_async_cpy
        width, height, depth = self.dimensions
        n_channel = self.n_channels

        dim = 3 if depth != 0 else 2 if height != 0 else 1
        shape = (depth, height, n_channel*width) if dim == 3 else \
                (height, n_channel*width) if dim == 2 else \
                (n_channel*width,)

        # generate input data and allocate output buffer
        if self.dtype in (numpy.float16, numpy.float32):
            arr = xp.random.random(shape).astype(self.dtype)
            kind = runtime.cudaChannelFormatKindFloat
        else:  # int
            # randint() in NumPy <= 1.10 does not have the dtype argument...
            arr = xp.random.randint(100, size=shape).astype(self.dtype)
            if self.dtype in (numpy.int8, numpy.int16, numpy.int32):
                kind = runtime.cudaChannelFormatKindSigned
            else:
                kind = runtime.cudaChannelFormatKindUnsigned
        arr2 = xp.zeros_like(arr)

        assert arr.flags['C_CONTIGUOUS']
        assert arr2.flags['C_CONTIGUOUS']

        # create a CUDA array
        ch_bits = [0, 0, 0, 0]
        for i in range(n_channel):
            ch_bits[i] = arr.dtype.itemsize*8
        ch = ChannelFormatDescriptor(*ch_bits, kind)
        print(ch.get_channel_format())
        cu_arr = CUDAarray(ch, width, height, depth)

        # copy from input to CUDA array, and back to output
        cu_arr.copy_from(arr, stream)
        cu_arr.copy_to(arr2, stream)

        # check input and output are identical
        if stream is not None:
            dev.synchronize()
        assert (arr == arr2).all()


source = r'''
extern "C"{
__global__ void copyKernel1Dfetch(float* output,
                                  cudaTextureObject_t texObj,
                                  int width)
{
    unsigned int x = blockIdx.x * blockDim.x + threadIdx.x;

    // Read from texture and write to global memory
    if (x < width)
        output[x] = tex1Dfetch<float>(texObj, x);
}

__global__ void copyKernel1D(float* output,
                             cudaTextureObject_t texObj,
                             int width)
{
    unsigned int x = blockIdx.x * blockDim.x + threadIdx.x;

    // Read from texture and write to global memory
    float u = x;
    if (x < width)
        output[x] = tex1D<float>(texObj, u);
}

__global__ void copyKernel2D(float* output,
                             cudaTextureObject_t texObj,
                             int width, int height)
{
    unsigned int x = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int y = blockIdx.y * blockDim.y + threadIdx.y;

    // Read from texture and write to global memory
    float u = x;
    float v = y;
    if (x < width && y < height)
        output[y * width + x] = tex2D<float>(texObj, u, v);
}

__global__ void copyKernel3D(float* output,
                             cudaTextureObject_t texObj,
                             int width, int height, int depth)
{
    unsigned int x = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int y = blockIdx.y * blockDim.y + threadIdx.y;
    unsigned int z = blockIdx.z * blockDim.z + threadIdx.z;

    // Read from texture and write to global memory
    float u = x;
    float v = y;
    float w = z;
    if (x < width && y < height && z < depth)
        output[z*width*height+y*width+x] = tex3D<float>(texObj, u, v, w);
}

__global__ void copyKernel3D_4ch(float* output_x,
                                 float* output_y,
                                 float* output_z,
                                 float* output_w,
                                 cudaTextureObject_t texObj,
                                 int width, int height, int depth)
{
    unsigned int x = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int y = blockIdx.y * blockDim.y + threadIdx.y;
    unsigned int z = blockIdx.z * blockDim.z + threadIdx.z;
    float4 data;

    // Read from texture, separate channels, and write to global memory
    float u = x;
    float v = y;
    float w = z;
    if (x < width && y < height && z < depth) {
        data = tex3D<float4>(texObj, u, v, w);
        output_x[z*width*height+y*width+x] = data.x;
        output_y[z*width*height+y*width+x] = data.y;
        output_z[z*width*height+y*width+x] = data.z;
        output_w[z*width*height+y*width+x] = data.w;
    }
}
}
'''


@testing.gpu
@testing.parameterize(*testing.product({
    'dimensions': ((64, 0, 0), (64, 32, 0), (64, 32, 19)),
    'mem_type': ('CUDAarray', 'linear', 'pitch2D'),
}))
class TestTexture(unittest.TestCase):
    def test_fetch_float_texture(self):
        width, height, depth = self.dimensions
        dim = 3 if depth != 0 else 2 if height != 0 else 1

        if (self.mem_type == 'linear' and dim != 1) or \
           (self.mem_type == 'pitch2D' and dim != 2):
            print('The test case', self.dimensions, 'is inapplicable for',
                  self.mem_type, 'and thus skipped.')
            return

        # generate input data and allocate output buffer
        shape = (depth, height, width) if dim == 3 else \
                (height, width) if dim == 2 else \
                (width,)

        # prepare input, output, and texture memory
        tex_data = cupy.random.random(shape, dtype=cupy.float32)
        real_output = cupy.zeros_like(tex_data)
        ch = ChannelFormatDescriptor(32, 0, 0, 0,
                                     runtime.cudaChannelFormatKindFloat)
        assert tex_data.flags['C_CONTIGUOUS']
        assert real_output.flags['C_CONTIGUOUS']
        if self.mem_type == 'CUDAarray':
            arr = CUDAarray(ch, width, height, depth)
            expected_output = cupy.zeros_like(tex_data)
            assert expected_output.flags['C_CONTIGUOUS']
            # test bidirectional copy
            arr.copy_from(tex_data)
            arr.copy_to(expected_output)
        else:  # linear are pitch2D are backed by ndarray
            arr = tex_data
            expected_output = tex_data

        # create a texture object
        if self.mem_type == 'CUDAarray':
            res = ResourceDescriptor(runtime.cudaResourceTypeArray, cuArr=arr)
        elif self.mem_type == 'linear':
            res = ResourceDescriptor(runtime.cudaResourceTypeLinear,
                                     arr=arr,
                                     chDesc=ch,
                                     sizeInBytes=arr.size*arr.dtype.itemsize)
        else:  # pitch2D
            # In this case, we rely on the fact that the hand-picked array
            # shape meets the alignment requirement. This is CUDA's limitation,
            # see CUDA Runtime API reference guide. "TexturePitchAlignment" is
            # assumed to be 32, which should be applicable for most devices.
            res = ResourceDescriptor(runtime.cudaResourceTypePitch2D,
                                     arr=arr,
                                     chDesc=ch,
                                     width=width,
                                     height=height,
                                     pitchInBytes=width*arr.dtype.itemsize)
        address_mode = (runtime.cudaAddressModeClamp,
                        runtime.cudaAddressModeClamp)
        tex = TextureDescriptor(address_mode, runtime.cudaFilterModePoint,
                                runtime.cudaReadModeElementType)
        texobj = TextureObject(res, tex)

        # get and launch the kernel
        mod = cupy.RawModule(source)
        ker_name = 'copyKernel'
        ker_name += '3D' if dim == 3 else '2D' if dim == 2 else '1D'
        ker_name += 'fetch' if self.mem_type == 'linear' else ''
        ker = mod.get_function(ker_name)
        block = (4, 4, 2) if dim == 3 else (4, 4) if dim == 2 else (4,)
        grid = ()
        args = (real_output, texobj, width)
        if dim >= 1:
            grid_x = (width + block[0] - 1)//block[0]
            grid = grid + (grid_x,)
        if dim >= 2:
            grid_y = (height + block[1] - 1)//block[1]
            grid = grid + (grid_y,)
            args = args + (height,)
        if dim == 3:
            grid_z = (depth + block[2] - 1)//block[2]
            grid = grid + (grid_z,)
            args = args + (depth,)
        ker(grid, block, args)

        # validate result
        assert (real_output == expected_output).all()


@testing.gpu
class TestTextureVectorType(unittest.TestCase):
    def test_fetch_float4_texture(self):
        width = 47
        height = 39
        depth = 11
        n_channel = 4

        # generate input data and allocate output buffer
        in_shape = (depth, height, n_channel*width)
        out_shape = (depth, height, width)

        # prepare input, output, and texture memory
        tex_data = cupy.random.random(in_shape, dtype=cupy.float32)
        real_output_x = cupy.zeros(out_shape, dtype=cupy.float32)
        real_output_y = cupy.zeros(out_shape, dtype=cupy.float32)
        real_output_z = cupy.zeros(out_shape, dtype=cupy.float32)
        real_output_w = cupy.zeros(out_shape, dtype=cupy.float32)
        ch = ChannelFormatDescriptor(32, 32, 32, 32,
                                     runtime.cudaChannelFormatKindFloat)
        arr = CUDAarray(ch, width, height, depth)
        arr.copy_from(tex_data)

        # create a texture object
        res = ResourceDescriptor(runtime.cudaResourceTypeArray, cuArr=arr)
        address_mode = (runtime.cudaAddressModeClamp,
                        runtime.cudaAddressModeClamp)
        tex = TextureDescriptor(address_mode, runtime.cudaFilterModePoint,
                                runtime.cudaReadModeElementType)
        texobj = TextureObject(res, tex)

        # get and launch the kernel
        mod = cupy.RawModule(source)
        ker_name = 'copyKernel3D_4ch'
        ker = mod.get_function(ker_name)
        block = (4, 4, 2)
        grid = ((width + block[0] - 1)//block[0],
                (height + block[1] - 1)//block[1],
                (depth + block[2] - 1)//block[2])
        args = (real_output_x, real_output_y, real_output_z, real_output_w,
                texobj, width, height, depth)
        ker(grid, block, args)

        # validate result
        assert (real_output_x == tex_data[..., 0::4]).all()
        assert (real_output_y == tex_data[..., 1::4]).all()
        assert (real_output_z == tex_data[..., 2::4]).all()
        assert (real_output_w == tex_data[..., 3::4]).all()
