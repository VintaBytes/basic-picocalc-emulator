"""Framebuffer virtual RGBA 320x320, sin dependencias de GUI."""


class Framebuffer:
    def __init__(self, width=320, height=320):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 4)
        self.clear(0, 0, 0)

    def clear(self, red=0, green=0, blue=0):
        color = bytes((red, green, blue, 255))
        self.pixels[:] = color * (self.width * self.height)

    def pixel(self, x, y, red=255, green=255, blue=255):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            pos = 4 * (y * self.width + x)
            # Evitar la asignacion que construye un bytes temporal por pixel.
            # Las demos de fractales ejecutan esta ruta miles de veces.
            pixels = self.pixels
            pixels[pos] = red
            pixels[pos + 1] = green
            pixels[pos + 2] = blue
            pixels[pos + 3] = 255

    def get_pixel(self, x, y):
        pos = 4 * (y * self.width + x)
        return tuple(self.pixels[pos:pos+4])

    def blit(self, x1, y1, x2, y2, width, height):
        """Copy a rectangle within this plane, including overlapping areas.

        The input image is snapshotted before any destination write. Pixels
        outside either boundary are clipped; no host-memory access escapes
        the RGBA buffer.
        """
        x1, y1, x2, y2, width, height = map(int, (x1, y1, x2, y2, width, height))
        if width <= 0 or height <= 0:
            return
        # Iterate only the intersection where both source and target exist.
        left = max(0, -x1, -x2)
        top = max(0, -y1, -y2)
        right = min(width, self.width - x1, self.width - x2)
        bottom = min(height, self.height - y1, self.height - y2)
        if left >= right or top >= bottom:
            return
        stride = (right - left) * 4
        # Snapshot each source row, then commit the copies: overlap-safe.
        rows = [bytes(self.pixels[4 * ((y1 + dy) * self.width + x1 + left):
                                  4 * ((y1 + dy) * self.width + x1 + left) + stride])
                for dy in range(top, bottom)]
        for dy, data in zip(range(top, bottom), rows):
            dest = 4 * ((y2 + dy) * self.width + x2 + left)
            self.pixels[dest:dest + stride] = data

    def paste_rgba(self, data, image_width, image_height, x=0, y=0, *, skip_transparent=False):
        """Copia RGBA top-left sobre el buffer actual, con recorte por filas.

        No hace escalado: reproduce las dimensiones de la imagen de entrada.
        No interpreta alfa de forma especial: JPEG y BMP son opacos.
        """
        image_width, image_height = int(image_width), int(image_height)
        x, y = int(x), int(y)
        if image_width <= 0 or image_height <= 0:
            return
        if len(data) != image_width * image_height * 4:
            raise ValueError('Carga grafica: longitud RGBA invalida')
        left, top = max(0, -x), max(0, -y)
        right = min(image_width, self.width - x)
        bottom = min(image_height, self.height - y)
        if left >= right or top >= bottom:
            return
        span = (right - left) * 4
        for source_y in range(top, bottom):
            src = (source_y * image_width + left) * 4
            dst = ((y + source_y) * self.width + x + left) * 4
            if skip_transparent:
                # Modo PNG -1: conservar destino de cada pixel con alfa 0.
                for px in range(0, span, 4):
                    if data[src + px + 3] != 0:
                        self.pixels[dst + px:dst + px + 4] = data[src + px:src + px + 4]
            else:
                self.pixels[dst:dst + span] = data[src:src + span]

    def snapshot(self):
        return bytes(self.pixels)

    def to_bmp(self):
        """Exporta BMP Windows RGB de 24 bits, sin dependencias ni Qt.

        El framebuffer usa RGBA con origen superior izquierdo; BMP clásico
        almacena filas en orden inverso y en secuencia B, G, R.
        """
        import struct

        width, height = self.width, self.height
        stride = (width * 3 + 3) & ~3
        size = stride * height
        header = (b'BM' + struct.pack('<IHHI', 54 + size, 0, 0, 54)
                  + struct.pack('<IiiHHIIiiII', 40, width, height, 1, 24,
                                0, size, 2835, 2835, 0, 0))
        raw = self.pixels
        rows = bytearray(size)
        for y in range(height):
            dest = (height - 1 - y) * stride
            for x in range(width):
                source = (y * width + x) * 4
                offset = dest + x * 3
                rows[offset:offset + 3] = bytes((raw[source + 2],
                                                  raw[source + 1], raw[source]))
        return header + rows
