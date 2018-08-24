import decimal
from binascii import hexlify


class Decimal(decimal.Decimal):
    def __new__(cls, value):
        return super().__new__(cls, str(value))


def chunk_data(data, size):
    return (data[i:i + size] for i in range(0, len(data), size))


def int_to_unknown_bytes(num, byteorder='big'):
    """Converts an int to the least number of bytes as possible."""
    return num.to_bytes((num.bit_length() + 7) // 8 or 1, byteorder)


def bytes_to_hex(bytestr, upper=False):
    hexed = hexlify(bytestr).decode()
    return hexed.upper() if upper else hexed


def hex_to_bytes(hexed):

    if len(hexed) & 1:
        hexed = '0' + hexed

    return bytes.fromhex(hexed)


def int_to_hex(num, upper=False):
    hexed = hex(num)[2:]
    return hexed.upper() if upper else hexed


def hex_to_int(hexed):
    return int(hexed, 16)


def flip_hex_byte_order(string):
    return bytes_to_hex(hex_to_bytes(string)[::-1])


def int_to_varint(val):

    if val < 253:
        return val.to_bytes(1, 'little')
    elif val <= 65535:
        return b'\xfd'+val.to_bytes(2, 'little')
    elif val <= 4294967295:
        return b'\xfe'+val.to_bytes(4, 'little')
    else:
        return b'\xff'+val.to_bytes(8, 'little')


def script_push(val):

    if val <= 75:
        return int_to_unknown_bytes(val)
    elif val < 256:
        return b'\x4c'+int_to_unknown_bytes(val)
    elif val < 65536:
        return b'\x4d'+val.to_bytes(2, 'little')
    else:
        return b'\x4e'+val.to_bytes(4, 'little')


# Slicing functions returning the byte-data-stream splitted
def read_bytes(stream, bytes):
    return stream[0:bytes], stream[bytes:]


def read_var_string(stream):
    size, stream = read_var_int(stream)
    return read_bytes(stream, size)


def read_var_int(stream):
    if len(stream) == 0:
        return 0, stream
    val = int(bytes_to_hex(stream[0:1]), base=16)
    if val < 253:
        return val, stream[1:]
    return read_as_int(stream[1:], 2**(val-252))


def read_as_int(stream, bytes):
    return int(bytes_to_hex(stream[0:bytes][::-1]), base=16), stream[bytes:]


def read_segwit_string(stream):
    bytes, stream = read_var_int(stream)
    witness, stream = read_bytes(stream, bytes)
    return int_to_varint(bytes) + witness, stream


def get_signatures_from_script(script):
    """Returns a list of signatures retrieved from the provided (partially)
    signed multisig scriptSig.

    :param data: The partially-signed multisig scriptSig.
    :type data: ``bytes``
    :returns: A list of retrieved signature from the provided scriptSig.
    :rtype: A ``list`` of ``bytes`` signatures
    """
    script = script[1:]  # remove the first OP_0
    sigs = []
    val, script = read_var_int(script)
    while val <= 72:  # TODO: Make a better check if the data is a signature (using DER rules: https://bitcoin.stackexchange.com/questions/12554/why-the-signature-is-always-65-13232-bytes-long)
        if val != 0:  # For partially-signed scriptSigs the missing signatures are each indicated with 0x00 at the end.
            potential_sig, script = read_bytes(script, val)
            if bytes_to_hex(potential_sig[0:1]) == '30':
                sigs.append(potential_sig)
        if len(script) == 0:  # escape if we have run out of the script
            break
        val, script = read_var_int(script)

    return sigs
