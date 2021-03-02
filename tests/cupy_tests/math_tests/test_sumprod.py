import unittest

import numpy
import pytest

import cupy
import cupy.core._accelerator as _acc
from cupy.core import _cub_reduction
from cupy import testing


@testing.gpu
class TestSumprod(unittest.TestCase):

    def tearDown(self):
        # Free huge memory for slow test
        cupy.get_default_memory_pool().free_all_blocks()
        cupy.get_default_pinned_memory_pool().free_all_blocks()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_all(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return a.sum()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_all_keepdims(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return a.sum(keepdims=True)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_external_sum_all(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return xp.sum(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_all2(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40), xp, dtype)
        return a.sum()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_all_transposed(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype).transpose(2, 0, 1)
        return a.sum()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_all_transposed2(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40), xp, dtype).transpose(2, 0, 1)
        return a.sum()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_axis(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return a.sum(axis=1)

    @testing.slow
    @testing.numpy_cupy_allclose()
    def test_sum_axis_huge(self, xp):
        a = testing.shaped_random((2048, 1, 1024), xp, 'b')
        a = xp.broadcast_to(a, (2048, 1024, 1024))
        return a.sum(axis=2)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_external_sum_axis(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return xp.sum(a, axis=1)

    # float16 is omitted, since NumPy's sum on float16 arrays has more error
    # than CuPy's.
    @testing.for_all_dtypes(no_float16=True)
    @testing.numpy_cupy_allclose()
    def test_sum_axis2(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40), xp, dtype)
        return a.sum(axis=1)

    def test_sum_axis2_float16(self):
        # Note that the above test example overflows in float16. We use a
        # smaller array instead.
        a = testing.shaped_arange((2, 30, 4), dtype='e')
        sa = a.sum(axis=1)
        b = testing.shaped_arange((2, 30, 4), numpy, dtype='f')
        sb = b.sum(axis=1)
        testing.assert_allclose(sa, sb.astype('e'))

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(contiguous_check=False)
    def test_sum_axis_transposed(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype).transpose(2, 0, 1)
        return a.sum(axis=1)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(contiguous_check=False)
    def test_sum_axis_transposed2(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40), xp, dtype).transpose(2, 0, 1)
        return a.sum(axis=1)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_axes(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4, 5), xp, dtype)
        return a.sum(axis=(1, 3))

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(rtol=1e-4)
    def test_sum_axes2(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40, 50), xp, dtype)
        return a.sum(axis=(1, 3))

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(rtol=1e-6)
    def test_sum_axes3(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4, 5), xp, dtype)
        return a.sum(axis=(0, 2, 3))

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(rtol=1e-6)
    def test_sum_axes4(self, xp, dtype):
        a = testing.shaped_arange((20, 30, 40, 50), xp, dtype)
        return a.sum(axis=(0, 2, 3))

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_empty_axis(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4, 5), xp, dtype)
        return a.sum(axis=())

    @testing.for_all_dtypes_combination(names=['src_dtype', 'dst_dtype'])
    @testing.numpy_cupy_allclose()
    def test_sum_dtype(self, xp, src_dtype, dst_dtype):
        if not xp.can_cast(src_dtype, dst_dtype):
            pytest.skip()
        a = testing.shaped_arange((2, 3, 4), xp, src_dtype)
        return a.sum(dtype=dst_dtype)

    @testing.for_all_dtypes_combination(names=['src_dtype', 'dst_dtype'])
    @testing.numpy_cupy_allclose()
    def test_sum_keepdims_and_dtype(self, xp, src_dtype, dst_dtype):
        if not xp.can_cast(src_dtype, dst_dtype):
            pytest.skip()
        a = testing.shaped_arange((2, 3, 4), xp, src_dtype)
        return a.sum(axis=2, dtype=dst_dtype, keepdims=True)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_keepdims_multiple_axes(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return a.sum(axis=(1, 2), keepdims=True)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_sum_out(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        b = xp.empty((2, 4), dtype=dtype)
        a.sum(axis=1, out=b)
        return b

    def test_sum_out_wrong_shape(self):
        a = testing.shaped_arange((2, 3, 4))
        b = cupy.empty((2, 3))
        with self.assertRaises(ValueError):
            a.sum(axis=1, out=b)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_prod_all(self, xp, dtype):
        a = testing.shaped_arange((2, 3), xp, dtype)
        return a.prod()

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_external_prod_all(self, xp, dtype):
        a = testing.shaped_arange((2, 3), xp, dtype)
        return xp.prod(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_prod_axis(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return a.prod(axis=1)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_external_prod_axis(self, xp, dtype):
        a = testing.shaped_arange((2, 3, 4), xp, dtype)
        return xp.prod(a, axis=1)

    @testing.for_all_dtypes_combination(names=['src_dtype', 'dst_dtype'])
    @testing.numpy_cupy_allclose()
    def test_prod_dtype(self, xp, src_dtype, dst_dtype):
        if not xp.can_cast(src_dtype, dst_dtype):
            pytest.skip()
        a = testing.shaped_arange((2, 3), xp, src_dtype)
        return a.prod(dtype=dst_dtype)


# This class compares CUB results against NumPy's
@testing.parameterize(*testing.product({
    'shape': [(10,), (10, 20), (10, 20, 30), (10, 20, 30, 40)],
    'order': ('C', 'F'),
    'backend': ('device', 'block'),
}))
@testing.gpu
@unittest.skipUnless(cupy.cuda.cub.available, 'The CUB routine is not enabled')
class TestCubReduction(unittest.TestCase):

    def setUp(self):
        self.old_routine_accelerators = _acc.get_routine_accelerators()
        self.old_reduction_accelerators = _acc.get_reduction_accelerators()
        if self.backend == 'device':
            _acc.set_routine_accelerators(['cub'])
            _acc.set_reduction_accelerators([])
        elif self.backend == 'block':
            _acc.set_routine_accelerators([])
            _acc.set_reduction_accelerators(['cub'])

    def tearDown(self):
        _acc.set_routine_accelerators(self.old_routine_accelerators)
        _acc.set_reduction_accelerators(self.old_reduction_accelerators)

    @testing.for_contiguous_axes()
    # sum supports less dtypes; don't test float16 as it's not as accurate?
    @testing.for_dtypes('qQfdFD')
    @testing.numpy_cupy_allclose(rtol=1E-5)
    def test_cub_sum(self, xp, dtype, axis):
        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)

        if xp is numpy:
            return a.sum(axis=axis)

        # xp is cupy, first ensure we really use CUB
        ret = cupy.empty(())  # Cython checks return type, need to fool it
        if self.backend == 'device':
            func_name = 'cupy.core._routines_math.cub.'
            if len(axis) == len(self.shape):
                func_name += 'device_reduce'
            else:
                func_name += 'device_segmented_reduce'
            with testing.AssertFunctionIsCalled(func_name, return_value=ret):
                a.sum(axis=axis)
        elif self.backend == 'block':
            # this is the only function we can mock; the rest is cdef'd
            func_name = 'cupy.core._cub_reduction.'
            func_name += '_SimpleCubReductionKernel_get_cached_function'
            func = _cub_reduction._SimpleCubReductionKernel_get_cached_function
            if len(axis) == len(self.shape):
                times_called = 2  # two passes
            else:
                times_called = 1  # one pass
            with testing.AssertFunctionIsCalled(
                    func_name, wraps=func, times_called=times_called):
                a.sum(axis=axis)
        # ...then perform the actual computation
        return a.sum(axis=axis)

    # sum supports less dtypes; don't test float16 as it's not as accurate?
    @testing.for_dtypes('qQfdFD')
    @testing.numpy_cupy_allclose(rtol=1E-5, contiguous_check=False)
    def test_cub_sum_empty_axis(self, xp, dtype):
        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)
        return a.sum(axis=())

    @testing.for_contiguous_axes()
    # prod supports less dtypes; don't test float16 as it's not as accurate?
    @testing.for_dtypes('qQfdFD')
    @testing.numpy_cupy_allclose(rtol=1E-5)
    def test_cub_prod(self, xp, dtype, axis):
        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)

        if xp is numpy:
            return a.prod(axis=axis)

        # xp is cupy, first ensure we really use CUB
        ret = cupy.empty(())  # Cython checks return type, need to fool it
        if self.backend == 'device':
            func_name = 'cupy.core._routines_math.cub.'
            if len(axis) == len(self.shape):
                func_name += 'device_reduce'
            else:
                func_name += 'device_segmented_reduce'
            with testing.AssertFunctionIsCalled(func_name, return_value=ret):
                a.prod(axis=axis)
        elif self.backend == 'block':
            # this is the only function we can mock; the rest is cdef'd
            func_name = 'cupy.core._cub_reduction.'
            func_name += '_SimpleCubReductionKernel_get_cached_function'
            func = _cub_reduction._SimpleCubReductionKernel_get_cached_function
            if len(axis) == len(self.shape):
                times_called = 2  # two passes
            else:
                times_called = 1  # one pass
            with testing.AssertFunctionIsCalled(
                    func_name, wraps=func, times_called=times_called):
                a.prod(axis=axis)
        # ...then perform the actual computation
        return a.prod(axis=axis)

    # TODO(leofang): test axis after support is added
    # don't test float16 as it's not as accurate?
    @testing.for_dtypes('bhilBHILfdF')
    @testing.numpy_cupy_allclose(rtol=1E-4)
    def test_cub_cumsum(self, xp, dtype):
        if self.backend == 'block':
            raise unittest.SkipTest('does not support')

        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)

        if xp is numpy:
            return a.cumsum()

        # xp is cupy, first ensure we really use CUB
        ret = cupy.empty(())  # Cython checks return type, need to fool it
        func = 'cupy.core._routines_math.cub.device_scan'
        with testing.AssertFunctionIsCalled(func, return_value=ret):
            a.cumsum()
        # ...then perform the actual computation
        return a.cumsum()

    # TODO(leofang): test axis after support is added
    # don't test float16 as it's not as accurate?
    @testing.for_dtypes('bhilBHILfdF')
    @testing.numpy_cupy_allclose(rtol=1E-4)
    def test_cub_cumprod(self, xp, dtype):
        if self.backend == 'block':
            raise unittest.SkipTest('does not support')

        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)

        if xp is numpy:
            result = a.cumprod()
            return self._mitigate_cumprod(xp, dtype, result)

        # xp is cupy, first ensure we really use CUB
        ret = cupy.empty(())  # Cython checks return type, need to fool it
        func = 'cupy.core._routines_math.cub.device_scan'
        with testing.AssertFunctionIsCalled(func, return_value=ret):
            a.cumprod()
        # ...then perform the actual computation
        result = a.cumprod()
        return self._mitigate_cumprod(xp, dtype, result)

    def _mitigate_cumprod(self, xp, dtype, result):
        # for testing cumprod against complex arrays, the gotcha is CuPy may
        # produce only Inf at the position where NumPy starts to give NaN. So,
        # an error would be raised during assert_allclose where the positions
        # of NaNs are examined. Since this is both algorithm and architecture
        # dependent, we have no control over this behavior and can only
        # circumvent the issue by manually converting Inf to NaN
        if dtype in (numpy.complex64, numpy.complex128):
            pos = xp.where(xp.isinf(result))
            result[pos] = xp.nan + 1j * xp.nan
        return result


# This class compares cuTENSOR results against NumPy's
@testing.parameterize(*testing.product({
    'shape': [(10,), (10, 20), (10, 20, 30), (10, 20, 30, 40)],
    'order': ('C', 'F'),
}))
@testing.gpu
@unittest.skipUnless(cupy.cuda.cutensor.available,
                     'The cuTENSOR routine is not enabled')
class TestCuTensorReduction(unittest.TestCase):

    def setUp(self):
        self.old_accelerators = cupy.core.get_routine_accelerators()
        cupy.core.set_routine_accelerators(['cutensor'])

    def tearDown(self):
        cupy.core.set_routine_accelerators(self.old_accelerators)

    @testing.for_contiguous_axes()
    # sum supports less dtypes; don't test float16 as it's not as accurate?
    @testing.for_dtypes('lLfdFD')
    @testing.numpy_cupy_allclose(rtol=1E-5, contiguous_check=False)
    def test_cutensor_sum(self, xp, dtype, axis):
        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)

        if xp is numpy:
            return a.sum(axis=axis)

        # xp is cupy, first ensure we really use cuTENSOR
        ret = cupy.empty(())  # Cython checks return type, need to fool it
        func = 'cupy.cutensor._try_reduction_routine'
        with testing.AssertFunctionIsCalled(func, return_value=ret):
            a.sum(axis=axis)
        # ...then perform the actual computation
        return a.sum(axis=axis)

    # sum supports less dtypes; don't test float16 as it's not as accurate?
    @testing.for_dtypes('lLfdFD')
    @testing.numpy_cupy_allclose(rtol=1E-5, contiguous_check=False)
    def test_cutensor_sum_empty_axis(self, xp, dtype):
        a = testing.shaped_random(self.shape, xp, dtype)
        if self.order in ('c', 'C'):
            a = xp.ascontiguousarray(a)
        elif self.order in ('f', 'F'):
            a = xp.asfortranarray(a)
        return a.sum(axis=())


@testing.parameterize(
    *testing.product({
        'shape': [(2, 3, 4), (20, 30, 40)],
        'axis': [0, 1],
        'transpose_axes': [True, False],
        'keepdims': [True, False],
        'func': ['nansum', 'nanprod']
    })
)
@testing.gpu
class TestNansumNanprodLong(unittest.TestCase):

    def _do_transposed_axis_test(self):
        return not self.transpose_axes and self.axis != 1

    def _numpy_nanprod_implemented(self):
        return (self.func == 'nanprod' and
                numpy.__version__ >= numpy.lib.NumpyVersion('1.10.0'))

    def _test(self, xp, dtype):
        a = testing.shaped_arange(self.shape, xp, dtype)
        if self.transpose_axes:
            a = a.transpose(2, 0, 1)
        if not issubclass(dtype, xp.integer):
            a[:, 1] = xp.nan
        func = getattr(xp, self.func)
        return func(a, axis=self.axis, keepdims=self.keepdims)

    @testing.for_all_dtypes(no_bool=True, no_float16=True)
    @testing.numpy_cupy_allclose()
    def test_nansum_all(self, xp, dtype):
        if (not self._numpy_nanprod_implemented() or
                not self._do_transposed_axis_test()):
            return xp.array(())
        return self._test(xp, dtype)

    @testing.for_all_dtypes(no_bool=True, no_float16=True)
    @testing.numpy_cupy_allclose(contiguous_check=False)
    def test_nansum_axis_transposed(self, xp, dtype):
        if (not self._numpy_nanprod_implemented() or
                not self._do_transposed_axis_test()):
            return xp.array(())
        return self._test(xp, dtype)


@testing.parameterize(
    *testing.product({
        'shape': [(2, 3, 4), (20, 30, 40)],
    })
)
@testing.gpu
class TestNansumNanprodExtra(unittest.TestCase):

    def test_nansum_axis_float16(self):
        # Note that the above test example overflows in float16. We use a
        # smaller array instead, return True if array is too large.
        if (numpy.prod(self.shape) > 24):
            return True
        a = testing.shaped_arange(self.shape, dtype='e')
        a[:, 1] = cupy.nan
        sa = cupy.nansum(a, axis=1)
        b = testing.shaped_arange(self.shape, numpy, dtype='f')
        b[:, 1] = numpy.nan
        sb = numpy.nansum(b, axis=1)
        testing.assert_allclose(sa, sb.astype('e'))

    @testing.for_all_dtypes(no_bool=True, no_float16=True)
    @testing.numpy_cupy_allclose()
    def test_nansum_out(self, xp, dtype):
        a = testing.shaped_arange(self.shape, xp, dtype)
        if not issubclass(dtype, xp.integer):
            a[:, 1] = xp.nan
        b = xp.empty((self.shape[0], self.shape[2]), dtype=dtype)
        xp.nansum(a, axis=1, out=b)
        return b

    def test_nansum_out_wrong_shape(self):
        a = testing.shaped_arange(self.shape)
        a[:, 1] = cupy.nan
        b = cupy.empty((2, 3))
        with self.assertRaises(ValueError):
            cupy.nansum(a, axis=1, out=b)


@testing.parameterize(
    *testing.product({
        'shape': [(2, 3, 4, 5), (20, 30, 40, 50)],
        'axis': [(1, 3), (0, 2, 3)],
    })
)
@testing.gpu
class TestNansumNanprodAxes(unittest.TestCase):
    @testing.for_all_dtypes(no_bool=True, no_float16=True)
    @testing.numpy_cupy_allclose(rtol=1e-6)
    def test_nansum_axes(self, xp, dtype):
        a = testing.shaped_arange(self.shape, xp, dtype)
        if not issubclass(dtype, xp.integer):
            a[:, 1] = xp.nan
        return xp.nansum(a, axis=self.axis)


@testing.gpu
class TestNansumNanprodHuge(unittest.TestCase):
    def _test(self, xp, nan_slice):
        a = testing.shaped_random((2048, 1, 1024), xp, 'f')
        a[nan_slice] = xp.nan
        a = xp.broadcast_to(a, (2048, 1024, 1024))
        return xp.nansum(a, axis=2)

    @testing.slow
    @testing.numpy_cupy_allclose(atol=1e-1)
    def test_nansum_axis_huge(self, xp):
        return self._test(
            xp, (slice(None, None), slice(None, None), slice(1, 2)))

    @testing.slow
    @testing.numpy_cupy_allclose(atol=1e-2)
    def test_nansum_axis_huge_halfnan(self, xp):
        return self._test(
            xp, (slice(None, None), slice(None, None), slice(0, 512)))


axes = [0, 1, 2]


@testing.parameterize(*testing.product({'axis': axes}))
@testing.gpu
class TestCumsum(unittest.TestCase):

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        return xp.cumsum(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_out(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        out = xp.zeros((5,), dtype=dtype)
        xp.cumsum(a, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_out_noncontiguous(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        out = xp.zeros((10,), dtype=dtype)[::2]  # Non contiguous view
        xp.cumsum(a, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_2dim(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.cumsum(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(contiguous_check=False)
    def test_cumsum_axis(self, xp, dtype):
        n = len(axes)
        a = testing.shaped_arange(tuple(range(4, 4 + n)), xp, dtype)
        return xp.cumsum(a, axis=self.axis)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_axis_out(self, xp, dtype):
        n = len(axes)
        shape = tuple(range(4, 4 + n))
        a = testing.shaped_arange(shape, xp, dtype)
        out = xp.zeros(shape, dtype=dtype)
        xp.cumsum(a, axis=self.axis, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_axis_out_noncontiguous(self, xp, dtype):
        n = len(axes)
        shape = tuple(range(4, 4 + n))
        a = testing.shaped_arange(shape, xp, dtype)
        out = xp.zeros((8,)+shape[1:], dtype=dtype)[::2]  # Non contiguous view
        xp.cumsum(a, axis=self.axis, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(contiguous_check=False)
    def test_ndarray_cumsum_axis(self, xp, dtype):
        n = len(axes)
        a = testing.shaped_arange(tuple(range(4, 4 + n)), xp, dtype)
        return a.cumsum(axis=self.axis)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumsum_axis_empty(self, xp, dtype):
        n = len(axes)
        a = testing.shaped_arange(tuple(range(0, n)), xp, dtype)
        return xp.cumsum(a, axis=self.axis)

    @testing.for_all_dtypes()
    def test_invalid_axis_lower1(self, dtype):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((4, 5), xp, dtype)
            with pytest.raises(numpy.AxisError):
                xp.cumsum(a, axis=-a.ndim - 1)

    @testing.for_all_dtypes()
    def test_invalid_axis_lower2(self, dtype):
        a = testing.shaped_arange((4, 5), cupy, dtype)
        with self.assertRaises(numpy.AxisError):
            return cupy.cumsum(a, axis=-a.ndim - 1)

    @testing.for_all_dtypes()
    def test_invalid_axis_upper1(self, dtype):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((4, 5), xp, dtype)
            with pytest.raises(numpy.AxisError):
                xp.cumsum(a, axis=a.ndim + 1)

    @testing.for_all_dtypes()
    def test_invalid_axis_upper2(self, dtype):
        a = testing.shaped_arange((4, 5), cupy, dtype)
        with self.assertRaises(numpy.AxisError):
            return cupy.cumsum(a, axis=a.ndim + 1)

    def test_cumsum_arraylike(self):
        with self.assertRaises(TypeError):
            return cupy.cumsum((1, 2, 3))

    @testing.for_float_dtypes()
    def test_cumsum_numpy_array(self, dtype):
        a_numpy = numpy.arange(8, dtype=dtype)
        with self.assertRaises(TypeError):
            return cupy.cumsum(a_numpy)


@testing.gpu
class TestCumprod(unittest.TestCase):

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumprod_1dim(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        return xp.cumprod(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumprod_out(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        out = xp.zeros((5,), dtype=dtype)
        xp.cumprod(a, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumprod_out_noncontiguous(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        out = xp.zeros((10,), dtype=dtype)[::2]  # Non contiguous view
        xp.cumprod(a, out=out)
        return out

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose(rtol=1e-6)
    def test_cumprod_2dim_without_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.cumprod(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_cumprod_2dim_with_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.cumprod(a, axis=1)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_ndarray_cumprod_2dim_with_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return a.cumprod(axis=1)

    @testing.slow
    def test_cumprod_huge_array(self):
        size = 2 ** 32
        # Free huge memory for slow test
        cupy.get_default_memory_pool().free_all_blocks()
        a = cupy.ones(size, 'b')
        result = cupy.cumprod(a, dtype='b')
        del a
        assert (result == 1).all()
        # Free huge memory for slow test
        del result
        cupy.get_default_memory_pool().free_all_blocks()

    @testing.for_all_dtypes()
    def test_invalid_axis_lower1(self, dtype):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((4, 5), xp, dtype)
            with pytest.raises(numpy.AxisError):
                xp.cumprod(a, axis=-a.ndim - 1)

    @testing.for_all_dtypes()
    def test_invalid_axis_lower2(self, dtype):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((4, 5), xp, dtype)
            with pytest.raises(numpy.AxisError):
                xp.cumprod(a, axis=-a.ndim - 1)

    @testing.for_all_dtypes()
    def test_invalid_axis_upper1(self, dtype):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((4, 5), xp, dtype)
            with pytest.raises(numpy.AxisError):
                return xp.cumprod(a, axis=a.ndim)

    @testing.for_all_dtypes()
    def test_invalid_axis_upper2(self, dtype):
        a = testing.shaped_arange((4, 5), cupy, dtype)
        with self.assertRaises(numpy.AxisError):
            return cupy.cumprod(a, axis=a.ndim)

    def test_cumprod_arraylike(self):
        with self.assertRaises(TypeError):
            return cupy.cumprod((1, 2, 3))

    @testing.for_float_dtypes()
    def test_cumprod_numpy_array(self, dtype):
        a_numpy = numpy.arange(1, 6, dtype=dtype)
        with self.assertRaises(TypeError):
            return cupy.cumprod(a_numpy)


@testing.gpu
class TestDiff(unittest.TestCase):

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_1dim(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        return xp.diff(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_1dim_with_n(self, xp, dtype):
        a = testing.shaped_arange((5,), xp, dtype)
        return xp.diff(a, n=3)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_without_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.diff(a)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_with_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.diff(a, axis=-2)

    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_with_n_and_axis(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.diff(a, 2, 1)

    @testing.with_requires('numpy>=1.16')
    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_with_prepend(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        b = testing.shaped_arange((4, 1), xp, dtype)
        return xp.diff(a, axis=-1, prepend=b)

    @testing.with_requires('numpy>=1.16')
    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_with_append(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        b = testing.shaped_arange((1, 5), xp, dtype)
        return xp.diff(a, axis=0, append=b, n=2)

    @testing.with_requires('numpy>=1.16')
    @testing.for_all_dtypes()
    @testing.numpy_cupy_allclose()
    def test_diff_2dim_with_scalar_append(self, xp, dtype):
        a = testing.shaped_arange((4, 5), xp, dtype)
        return xp.diff(a, prepend=1, append=0)

    @testing.with_requires('numpy>=1.16')
    def test_diff_invalid_axis(self):
        for xp in (numpy, cupy):
            a = testing.shaped_arange((2, 3, 4), xp)
            with pytest.raises(numpy.AxisError):
                xp.diff(a, axis=3)
            with pytest.raises(numpy.AxisError):
                xp.diff(a, axis=-4)
