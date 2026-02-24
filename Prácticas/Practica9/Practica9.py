import struct
import hashlib
import random
import math

# reutilizamos leer_bmp y guardar_bmp de práctica 1

def leer_bmp(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    offset = struct.unpack_from('<I', data, 10)[0]
    width  = struct.unpack_from('<i', data, 18)[0]
    height = struct.unpack_from('<i', data, 22)[0]

    header = bytearray(data[:offset])
    pixels = bytearray(data[offset:])

    return header, pixels, width, height


def guardar_bmp(filepath, header, pixels):
    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(pixels)


# ==============================
# CIFRADO
# ==============================

def derivar_clave(password, longitud):
    clave = b''
    contador = 0

    while len(clave) < longitud:
        bloque = hashlib.sha256(
            password.encode() + struct.pack('<I', contador)
        ).digest()
        clave += bloque
        contador += 1

    return clave[:longitud]


def cifrar_xor(mensaje, password):
    clave = derivar_clave(password, len(mensaje))
    return bytes(m ^ k for m, k in zip(mensaje, clave))


# ==============================
# POSICIONES ALEATORIAS
# ==============================

def semilla_de_password(password):
    hash_bytes = hashlib.sha256(password.encode()).digest()
    return int.from_bytes(hash_bytes[:8], 'big')


def seleccionar_posiciones(total_bytes, n_bits, seed):
    rng = random.Random(seed)
    posiciones = rng.sample(range(total_bytes), n_bits)
    return sorted(posiciones)


# ==============================
# EMBED SEGURO
# ==============================

def embed_secure(src, dst, mensaje, password):
    header, pixels, w, h = leer_bmp(src)

    msg_bytes = mensaje.encode('utf-8')
    cifrado   = cifrar_xor(msg_bytes, password)

    datos = struct.pack('<I', len(msg_bytes)) + cifrado

    bits = []
    for byte in datos:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    if len(bits) > len(pixels):
        raise ValueError("Mensaje demasiado grande")

    seed = semilla_de_password(password)
    posiciones = seleccionar_posiciones(len(pixels), len(bits), seed)

    pixels_mod = bytearray(pixels)

    for pos, bit in zip(posiciones, bits):
        pixels_mod[pos] = (pixels_mod[pos] & 0xFE) | bit

    guardar_bmp(dst, header, pixels_mod)


def extract_secure(stego, password):
    _, pixels, _, _ = leer_bmp(stego)

    seed = semilla_de_password(password)

    pos_long = seleccionar_posiciones(len(pixels), 32, seed)

    msg_len = 0
    for p in pos_long:
        msg_len = (msg_len << 1) | (pixels[p] & 1)

    total_bits = 32 + msg_len * 8
    posiciones = seleccionar_posiciones(len(pixels), total_bits, seed)

    bits = [pixels[p] & 1 for p in posiciones[32:]]

    cifrado = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | bit
        cifrado.append(byte)

    return cifrar_xor(bytes(cifrado), password).decode('utf-8')
