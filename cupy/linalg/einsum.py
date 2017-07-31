import collections
import string

import numpy
import six

import cupy


class SingleViewCalculator(object):
    """Calculate 'ii->i' by cupy.diagonal if needed.

    Args:
        ioperand (cupy.ndarray): Array to be calculated diagonal.
        subscript (str):
            Specifies the subscripts. If the same label appears
            more than once, calculate diagonal for those axes.
    """

    def __init__(self, ioperand, subscript):
        self.subscript = subscript
        self.ioperand = ioperand
        self.labels = set(self.subscript)
        self.label_to_axis = collections.defaultdict(list)
        for i, label in enumerate(subscript):
            self.label_to_axis[label].append(i)

    def __call__(self):
        self.result = self.ioperand
        count_dict = collections.Counter(self.subscript)
        for label in self.labels:
            if count_dict[label] == 1:
                continue
            axes_to_diag = []
            for i, char in enumerate(self.subscript):
                if char == label:
                    axes_to_diag.append(i)
            for axis in reversed(axes_to_diag[1:]):
                self.result = self.result.diagonal(0, axis, axes_to_diag[0])
                self.result = cupy.rollaxis(self.result, -1, axes_to_diag[0])
                self.subscript = self.subscript[:axis] + \
                    self.subscript[axis + 1:]


class SummedViewCalculator(object):
    """Calculate 'i->' by cupy.sum if needed.

    Args:
        ioperand (cupy.ndarray): Array to be summed.
        input_subscript (str): Specifies the subscripts for input array.
        output_subscript (str):
            Specifies the subscripts for output array. If one label exists in
            input_subscript but not in output_subscript, this label will be
            summed.
    """

    def __init__(self, ioperand, input_subscript, output_subscript):
        self.ioperand = ioperand
        self.subscript = input_subscript
        self.label_to_summed = set(input_subscript) - set(output_subscript)
        self.axes_to_summed = []
        for i, label in enumerate(input_subscript):
            if label in self.label_to_summed:
                self.axes_to_summed.append(i)

    def __call__(self):
        if self.axes_to_summed:
            self.result = self.ioperand.sum(axis=tuple(self.axes_to_summed)). \
                astype(self.ioperand)
        else:
            self.result = self.ioperand
        for label in self.label_to_summed:
            self.subscript = self.subscript.replace(label, '')


class TransposedViewCalculator(object):
    """Calculate 'ij->ji' by cupy.transpose if needed.

    Args:
        ioperand (cupy.ndarray): Array to be transpose.
        input_subscript (str): Specifies the subscripts for input arrays.
        output_subscript (str):
            Specifies the subscripts for output arrays. If input does not
            match output, ``operand`` is transposed so that it matches.
    """

    def __init__(self, ioperand, input_subscript, output_subscript):
        assert len(input_subscript) == len(output_subscript)
        assert set(input_subscript) == set(output_subscript)
        self.ioperand = ioperand
        self.input_subscript = input_subscript
        self.output_subscript = output_subscript

    def __call__(self):
        transpose_orders = []
        for label in self.output_subscript:
            transpose_orders.append(self.input_subscript.find(label))
        if transpose_orders == sorted(transpose_orders):
            self.result = self.ioperand
        else:
            self.result = self.ioperand.transpose(transpose_orders)


class CombinedViewCalculator(object):
    """Calculate 'i,j->ij' by cupy.tensordot.

    Args:
        ioperands (sequence of arrays): Arrays to be combined.
        subscripts (sequence of str): Specifies the subscripts.
    """

    def __init__(self, ioperands, subscripts):
        self.ioperands = ioperands
        self.subscripts = subscripts

    def __call__(self):
        self.result = self.ioperands[0]
        for ioperand in self.ioperands[1:]:
            # TODO(fukatani): add up at here if enable.
            self.result = cupy.tensordot(self.result, ioperand, axes=0)
        self.subscript = ''.join(self.subscripts)


def get_dummy_labels(label_list):
    dummy_label_set = set([])
    count_dict = collections.Counter(label_list)
    for label, count in count_dict.items():
        if count >= 2:
            dummy_label_set.add(label)
    return dummy_label_set


def einsum(*operands):
    """Evaluates the Einstein summation convention on the operands.

    Using the Einstein summation convention, many common multi-dimensional
    array operations can be represented in a simple fashion. This function
    provides a way to compute such summations.

    Args:
        subscripts (str): Specifies the subscripts for summation.
        operands (sequence of arrays): These are the arrays for the operation.

    Returns:
        cupy.ndarray:
            The calculation based on the Einstein summation convention.

    .. seealso:: :func:`numpy.einsum`
    """

    # TODO(fukatani): Support 'out', 'order', 'dtype', 'casting', 'optimize'

    if not operands:
        raise ValueError('must specify the einstein sum subscripts string and '
                         'at least one operand, or at least one operand and '
                         'its corresponding subscripts list')

    subscripts = operands[0]
    ioperands = operands[1:]

    if not isinstance(subscripts, str):
        raise TypeError('Current cupy einsum support only string subscripts')

    # TODO(fukatani): Support '...'
    if '.' in subscripts:
        raise TypeError('Current cupy einsum does not support \'...\' '
                        'ellipsis')

    subscripts = subscripts.replace(' ', '')
    irregular_chars = set(subscripts) - set(string.ascii_letters) - set('->,')
    if irregular_chars:
        pickup = list(irregular_chars)[0]
        raise ValueError('invalid subscript \'{}\' in einstein sum subscripts '
                         'string, subscripts must be letters'.format(pickup))

    converted_inputs = []
    dtype = numpy.result_type(*ioperands)
    for a in ioperands:
        if isinstance(a, cupy.ndarray):
            converted_inputs.append(a.astype(dtype))
        else:
            converted_inputs.append(cupy.asarray(a, dtype=dtype))

    pos = subscripts.find('-')
    if pos == len(subscripts) - 1:
        raise ValueError('einstein sum subscript string does not contain '
                         'proper \'->\' output specified')
    if pos != -1 and subscripts[pos + 1] != '>':
        raise ValueError('einstein sum subscript string does not contain '
                         'proper \'->\' output specified')

    arrow_pos = subscripts.find('->')
    if arrow_pos == -1:
        input_subscripts = subscripts
        label_list = list(input_subscripts.replace(',', ''))
        out_label_set = set(label_list) - get_dummy_labels(label_list)
        output_subscript = ''.join(sorted(list(out_label_set)))
    else:
        input_subscripts = subscripts[:arrow_pos]
        output_subscript = subscripts[arrow_pos + 2:]

        irregular_chars = set(output_subscript) - set(input_subscripts)
        if irregular_chars:
            pickup = list(irregular_chars)[0]
            raise ValueError('einstein sum subscripts string included output '
                             'subscript \'{}\' which never appeared in an '
                             'input'.format(pickup))

        count_dict = collections.Counter(output_subscript)
        for key in count_dict:
            if count_dict[key] == 1:
                continue
            raise ValueError('einstein sum subscripts string includes output '
                             'subscript \'{}\' multiple times'.format(key))

    input_subscripts_list = input_subscripts.split(',')
    if len(input_subscripts_list) < len(converted_inputs):
        raise ValueError('fewer operands provided to einstein sum function '
                         'than specified in the subscripts string')
    if len(input_subscripts_list) > len(converted_inputs):
        raise ValueError('more operands provided to einstein sum function '
                         'than specified in the subscripts string')

    i_parsers = []
    for i in six.moves.range(len(input_subscripts_list)):
        subscript = input_subscripts_list[i]
        ioperand = converted_inputs[i]
        if len(subscript) > ioperand.ndim:
            raise ValueError('einstein sum subscripts string contains too '
                             'many subscripts for operand {}'.format(i))
        if len(subscript) < ioperand.ndim:
            raise ValueError('operand has more dimensions than subscripts'
                             ' given in einstein sum, but no \'...\' ellipsis'
                             ' provided to broadcast the extra dimensions.')

        calc = SingleViewCalculator(ioperand, subscript)
        calc()
        i_parsers.append(calc)

    if len(converted_inputs) >= 2:
        i_subscripts = [i_parser.subscript for i_parser in i_parsers]
        i_results = [i_parser.result for i_parser in i_parsers]
        calc = CombinedViewCalculator(i_results, i_subscripts)
        calc()
        calc = SingleViewCalculator(calc.result, calc.subscript)
        calc()
    else:
        calc = i_parsers[0]

    calc = SummedViewCalculator(calc.result, calc.subscript,
                                output_subscript)
    calc()
    calc = TransposedViewCalculator(calc.result, calc.subscript,
                                    output_subscript)
    calc()
    return calc.result
