"""Pantalla bitmap independiente de Qt, consola e instrucciones graficas.

Utiliza las tablas originales de FONT 1..8 cuando han sido importadas al
paquete, o conserva glifos de desarrollo como respaldo provisional.
"""
import math
from basic_cde.core.expressions import BasicError
from .framebuffer import Framebuffer
from .font8x12 import GLYPHS
from .font6x8 import GLYPHS_6X8
from .rom_fonts import DIMENSIONS, bundled_fonts


def rgb(value):
    value = int(value) & 0xFFFFFF
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


class BitmapDisplay:
    CHAR_W, CHAR_H = 8, 12
    # Dimensiones del manual PicoMite 6.00.01 para pantallas LCD.
    # Las fuentes importadas prevalecen sobre las aproximaciones de desarrollo.
    STANDARD_FONTS = DIMENSIONS

    def __init__(self, width=320, height=320):
        # N es la pantalla visible; F y L son planos fuera de pantalla.
        self.framebuffer = Framebuffer(width, height)
        self.buffers = {'N': self.framebuffer}
        self.blit_buffers = {}  # identificador -> (width, height, RGBA)
        self.sprite_buffers = {}  # independientes de BLIT; RGBA en paleta RGB121
        self.sprite_transparent = 0
        # Sprites mostrados: orden de composicion (LIFO por cada plano).
        # Cada registro almacena el fondo previo al dibujo del sprite.
        self.sprite_visible = {}  # id -> (target, x, y, layer, options, saved_background)
        self.sprite_order = []
        self.write_target = 'N'
        self.foreground = 0x00FF00
        self.background = 0
        self.col = 0
        self.row = 0
        self.fonts = {}
        self.rom_fonts = bundled_fonts()
        self.current_font = 1
        self.font_scale = 1

    @property
    def _draw_buffer(self):
        """Returns the current drawing target, which need not be visible."""
        return self.buffers[self.write_target]

    def framebuffer_command(self, action, *args):
        """Virtual 320x320 N/F/L buffers. No physical-device side effects.

        This is the LCD-style explicit-copy model: WRITE chooses where
        subsequent drawing goes; COPY updates the destination immediately.
        """
        action = action.upper()
        if action in ('CREATE', 'LAYER'):
            destination = 'F' if action == 'CREATE' else 'L'
            if args:
                raise BasicError(f'FRAMEBUFFER {action}: argumentos invalidos')
            if destination in self.buffers:
                raise BasicError('Framebuffer already exists')
            self.buffers[destination] = Framebuffer(self.framebuffer.width,
                                                    self.framebuffer.height)
            return
        if action == 'WRITE':
            if len(args) != 1 or args[0] not in self.buffers:
                raise BasicError('Invalid framebuffer')
            self.write_target = args[0]
            return
        if action == 'COPY':
            if len(args) not in (2, 3):
                raise BasicError('FRAMEBUFFER COPY: argumentos invalidos')
            src, dst = args[:2]
            if src not in self.buffers or dst not in self.buffers:
                raise BasicError('Invalid framebuffer')
            if len(args) == 3 and args[2] != 'B':
                raise BasicError('FRAMEBUFFER COPY: tercer argumento invalido')
            # B es asincrono en el equipo fisico; aqui la copia es sincrona.
            self.buffers[dst].pixels[:] = self.buffers[src].pixels
            return
        if action == 'CLOSE':
            if len(args) > 1 or (args and args[0] not in ('F', 'L')):
                raise BasicError('FRAMEBUFFER CLOSE: argumentos invalidos')
            targets = args if args else ('F', 'L')
            for target in targets:
                self.buffers.pop(target, None)
                if self.write_target == target:
                    self.write_target = 'N'
            return
        if action == 'WAIT':
            # All virtual copies complete synchronously. There is no
            # physical blanking interval to wait for on the host.
            if args:
                raise BasicError('FRAMEBUFFER WAIT: argumentos invalidos')
            return
        if action == 'MERGE':
            if len(args) > 2 or (len(args) == 2 and args[1] != 'B'):
                raise BasicError('FRAMEBUFFER MERGE: argumentos invalidos')
            if len(args) == 1 and args[0] == 'B':
                raise BasicError('FRAMEBUFFER MERGE: falta color')
            if 'F' not in self.buffers or 'L' not in self.buffers:
                raise BasicError('Invalid framebuffer')
            transparent_color = int(args[0]) & 0xFFFFFF if args else 0
            if 0 <= transparent_color <= 15:
                # LCD 4-bit RGB121 palette: bit 3 red, bits 2-1
                # green, bit 0 blue. Indices are NOT RGB integers.
                index = transparent_color
                transparent = (
                    255 if index & 8 else 0,
                    ((index >> 1) & 3) * 85,
                    255 if index & 1 else 0,
                )
            else:
                # Legacy RGB extension retained for 0.2.52 examples.
                transparent = rgb(transparent_color)
            base = self.buffers['F'].pixels
            layer = self.buffers['L'].pixels
            merged = self.framebuffer.pixels
            merged[:] = base
            # RGB transparent colour applies only to L. F and L unchanged.
            for offset in range(0, len(layer), 4):
                if (layer[offset], layer[offset + 1], layer[offset + 2]) != transparent:
                    merged[offset:offset + 4] = layer[offset:offset + 4]
            return
        raise BasicError(f'FRAMEBUFFER {action}: no disponible')

    def cls(self, color=None):
        color = self.background if color is None else int(color)
        self._draw_buffer.clear(*rgb(color))
        self.col = self.row = 0

    def _font_info(self, font):
        if font in self.fonts:
            return self.fonts[font][:2]
        if font in self.STANDARD_FONTS:
            return self.STANDARD_FONTS[font]
        raise BasicError(f'FONT {font}: fuente no definida')

    def glyph(self, x, y, ch, color=None, background=None, scale=1, font=None):
        font = self.current_font if font is None else int(font)
        width, height = self._font_info(font)
        code = ord(ch) if len(ch) == 1 else ord('?')
        if font in self.fonts:
            fw, fh, first, payload = self.fonts[font]
            rows = None
        elif font in self.STANDARD_FONTS and font in self.rom_fonts:
            rows = None
        elif font in self.STANDARD_FONTS:
            fallback_code = ord('x') if code == 250 else ord('?')
            if font == 7:
                rows = GLYPHS_6X8[code-32] if 32 <= code <= 126 else GLYPHS_6X8[fallback_code-32]
            else:
                rows = GLYPHS[code-32] if 32 <= code <= 126 else GLYPHS[fallback_code-32]
        fg = rgb(self.foreground if color is None else color)
        # En TEXT, si se omite el fondo se utiliza el color de fondo
        # activo de COLOR/COLOUR. El valor -1 pide transparencia real:
        # solo en ese caso dejamos intactos los pixeles apagados.
        # Antes se dejaban transparentes TODOS los TEXT sin fondo,
        # por eso Sokoban no borraba la figura en su celda anterior.
        if background is None:
            bg = rgb(self.background)
        elif int(background) == -1:
            bg = None
        else:
            bg = rgb(background)
        x, y, scale = int(x), int(y), int(scale)
        if scale < 1 or scale > 8:
            raise BasicError('Escala de fuente fuera de rango')
        for gy in range(height):
            for gx in range(width):
                if font in self.fonts:
                    # El indice lineal no completa filas hasta el byte siguiente.
                    bit = (code - first) * fw * fh + gy * fw + gx
                    ink = (code >= first and 0 <= bit // 8 < len(payload)
                           and bool(payload[bit // 8] & (0x80 >> (bit % 8))))
                elif font in self.rom_fonts:
                    ink = self.rom_fonts[font].pixel(code, gx, gy)
                elif font == 7:
                    ink = bool(rows[gy] & (0x80 >> gx))
                elif font in self.STANDARD_FONTS:
                    # Otras fuentes conservan por ahora la aproximacion.
                    sy = min(11, gy * 12 // height)
                    sx = min(7, gx * 8 // width)
                    ink = bool(rows[sy] & (0x80 >> sx))
                else:
                    byte = rows[gy * ((width + 7) // 8) + gx // 8]
                    ink = bool(byte & (0x80 >> (gx % 8)))
                tone = fg if ink else bg
                if tone is None:
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        self._draw_buffer.pixel(x + gx*scale + sx, y + gy*scale + sy, *tone)

    def scroll(self):
        fb = self._draw_buffer
        row_height = self._font_info(self.current_font)[1] * self.font_scale
        line_bytes = fb.width * 4 * row_height
        fb.pixels[:-line_bytes] = fb.pixels[line_bytes:]
        fb.pixels[-line_bytes:] = bytes((*rgb(self.background), 255)) * (fb.width * row_height)
        self.row = max(0, fb.height // row_height - 1)

    def console(self, text):
        cw, ch = self._font_info(self.current_font)
        cw *= self.font_scale
        ch *= self.font_scale
        max_cols = max(1, self._draw_buffer.width // cw)
        max_rows = max(1, self._draw_buffer.height // ch)
        for char in text:
            if char == '\r':
                self.col = 0
                continue
            if char == '\n':
                self.col = 0
                self.row += 1
            elif char == '\t':
                self.col = ((self.col // 4) + 1) * 4
            else:
                if self.col >= max_cols:
                    self.col, self.row = 0, self.row+1
                while self.row >= max_rows:
                    self.scroll()
                self.glyph(self.col*cw, self.row*ch, char,
                           background=self.background, scale=self.font_scale)
                self.col += 1
            while self.row >= max_rows:
                self.scroll()

    def line(self, x1, y1, x2, y2, color=None, thickness=1):
        x1,y1,x2,y2=map(lambda x:int(round(x)),(x1,y1,x2,y2))
        raw_width=int(1 if thickness is None else thickness)
        thickness=max(1,abs(raw_width))
        if thickness>100: raise BasicError('LINE: ancho excesivo')
        drawing_color=self.foreground if color is None else color

        # PicoMite: un ancho positivo en una LINE horizontal/vertical
        # parte del pixel de referencia hacia abajo/derecha; NO se centra.
        # Con ancho negativo se usa el modo centrado.
        # BOX relleno conserva la semantica y acelera los trazos rectos.
        if raw_width>=0 and thickness>1 and y1==y2:
            self.box(min(x1,x2), y1, abs(x2-x1)+1, thickness,
                     thickness=0, fill=drawing_color)
            return
        if raw_width>=0 and thickness>1 and x1==x2:
            self.box(x1, min(y1,y2), thickness, abs(y2-y1)+1,
                     thickness=0, fill=drawing_color)
            return

        # Lineas de 1 pixel, diagonales o anchos negativos:
        # conserva la rasterizacion existente, centrada cuando hay grosor.
        dx,dy=abs(x2-x1),abs(y2-y1)
        sx=1 if x1<x2 else -1
        sy=1 if y1<y2 else -1
        err=dx-dy
        tone=rgb(drawing_color)
        while True:
            for oy in range(-(thickness//2), -(thickness//2)+thickness):
                for ox in range(-(thickness//2), -(thickness//2)+thickness):
                    self._draw_buffer.pixel(x1+ox,y1+oy,*tone)
            if x1==x2 and y1==y2: break
            e2=2*err
            if e2>-dy: err-=dy; x1+=sx
            if e2<dx: err+=dx; y1+=sy

    def box(self, x,y,w,h,thickness=1,color=None,fill=None):
        x,y,w,h=map(int,(x,y,w,h))
        # Algunos programas PicoCalc dibujan cajas parcialmente fuera de pantalla
        # durante animaciones. Un ancho o alto no positivo no ocupa pixeles.
        # No normalizar valores negativos: invertirlos dibujaria otra figura.
        if w <= 0 or h <= 0:
            return
        if fill is not None:
            tone=rgb(fill)
            fb = self._draw_buffer
            x0, xend = max(0, x), min(fb.width, x + w)
            y0, yend = max(0, y), min(fb.height, y + h)
            if xend > x0 and yend > y0:
                row = bytes((*tone, 255)) * (xend - x0)
                for yy in range(y0, yend):
                    start = 4 * (yy * fb.width + x0)
                    fb.pixels[start:start + len(row)] = row
        if int(1 if thickness is None else thickness):
            self.line(x,y,x+w-1,y,color,thickness or 1)
            self.line(x,y+h-1,x+w-1,y+h-1,color,thickness or 1)
            self.line(x,y,x,y+h-1,color,thickness or 1)
            self.line(x+w-1,y,x+w-1,y+h-1,color,thickness or 1)

    def circle(self,x,y,r,thickness=1,aspect=1,color=None,fill=None):
        # MMBasic: un argumento opcional vacio usa su valor predeterminado.
        # CIRCLE X,Y,R,,,C,FILL omite LW y A; no equivale a aspecto 0.
        thickness = 1 if thickness is None else thickness
        aspect = 1.0 if aspect is None else aspect
        r=int(r)
        if r<0: raise BasicError('CIRCLE: radio negativo')
        if r>1000: raise BasicError('CIRCLE: radio excesivo')
        if not aspect: raise BasicError('CIRCLE: aspecto cero')
        if fill == -1:
            fill = None
        x,y=int(x),int(y)
        fb = self._draw_buffer
        a = float(aspect)
        rx = int(r * abs(a))
        border = max(0.7, int(thickness) / 2)
        border_on = int(thickness) > 0
        border_rgb = rgb(self.foreground if color is None else color)
        fill_rgb = rgb(fill) if fill is not None else None
        # Compare squared distances: avoid math.hypot (sqrt) per pixel.
        # The annulus thresholds are squared only once per CIRCLE.
        r2 = r * r
        inner2 = max(0.0, r - border) ** 2
        outer2 = (r + border) ** 2
        x0, xend = max(0, x - rx - 1), min(fb.width, x + rx + 2)
        y0, yend = max(0, y - r), min(fb.height, y + r + 1)
        inv_a2 = 1.0 / (a * a)
        pixels = fb.pixels
        for yy in range(y0, yend):
            dy2 = (yy - y) ** 2
            for xx in range(x0, xend):
                d2 = (xx - x) ** 2 * inv_a2 + dy2
                tone = None
                if fill_rgb is not None and d2 <= r2:
                    tone = fill_rgb
                if border_on and inner2 < d2 < outer2:
                    tone = border_rgb
                if tone is not None:
                    pos = 4 * (yy * fb.width + xx)
                    pixels[pos] = tone[0]
                    pixels[pos + 1] = tone[1]
                    pixels[pos + 2] = tone[2]
                    pixels[pos + 3] = 255

    def text(self,x,y,text,alignment='LT',font=None,scale=None,color=None,background=None):
        font = self.current_font if font is None else int(font)
        scale = self.font_scale if scale is None else int(scale)
        char_w, char_h = self._font_info(font)
        alignment = str(alignment).upper()
        if len(alignment) > 2 and alignment[2] != 'N':
            raise BasicError('TEXT: orientacion pendiente')
        width = len(str(text)) * char_w * scale
        height = char_h * scale
        if alignment[:1] == 'C': x -= width//2
        elif alignment[:1] == 'R': x -= width
        if len(alignment)>1 and alignment[1]=='M': y -= height//2
        elif len(alignment)>1 and alignment[1]=='B': y -= height
        for i, ch in enumerate(str(text)):
            self.glyph(int(x)+char_w*scale*i, int(y), ch, color, background, scale, font=font)

    def rbox(self, x, y, w, h, radius=None, color=None, fill=None):
        """Caja con esquinas redondeadas, radio en pixeles, clip 320x320."""
        x, y, w, h = map(int, (x, y, w, h))
        if w <= 0 or h <= 0:
            return
        r = min(max(0, int(10 if radius is None else radius)), w // 2, h // 2)
        border_color = rgb(self.foreground if color is None else color)
        fill_color = rgb(fill) if fill is not None and fill != -1 else None

        def inside(px, py, ox, oy, ow, oh, rad):
            if ow <= 0 or oh <= 0 or px < ox or py < oy or px >= ox + ow or py >= oy + oh:
                return False
            if rad <= 0:
                return True
            cx = ox + rad - 1 if px < ox + rad else (ox + ow - rad if px >= ox + ow - rad else px)
            cy = oy + rad - 1 if py < oy + rad else (oy + oh - rad if py >= oy + oh - rad else py)
            return (px - cx) ** 2 + (py - cy) ** 2 <= rad ** 2

        for py in range(max(0, y), min(self._draw_buffer.height, y + h)):
            for px in range(max(0, x), min(self._draw_buffer.width, x + w)):
                if not inside(px, py, x, y, w, h, r):
                    continue
                outline = not inside(px, py, x + 1, y + 1, w - 2, h - 2, max(0, r - 1))
                color_value = border_color if outline else fill_color
                if color_value is not None:
                    self._draw_buffer.pixel(px, py, *color_value)

    def polygon(self, count, xs, ys, border=None, fill=None):
        """POLYGON escalar: relleno con regla par/impar y bordes conectados.

        Las coordenadas se copian de los arreglos BASIC sin modificarlos;
        el relleno está recortado al framebuffer de 320x320.
        """
        if not isinstance(count, (int, float)) or int(count) != count or int(count) < 3:
            raise BasicError('POLYGON: numero de vertices invalido')
        count = int(count)
        if not hasattr(xs, 'items') or not hasattr(ys, 'items'):
            raise BasicError('POLYGON: se requieren arreglos de coordenadas')
        if len(xs.shape) != 1 or len(ys.shape) != 1 or len(xs.items) < count or len(ys.items) < count:
            raise BasicError('POLYGON: arreglos de vertices invalidos')
        points = [(float(xs.items[k]), float(ys.items[k])) for k in range(count)]
        for x, y in points:
            if not math.isfinite(x) or not math.isfinite(y):
                raise BasicError('POLYGON: coordenada no finita')
        if fill is not None and fill != -1:
            tone = rgb(fill)
            lower = max(0, int(math.floor(min(y for x, y in points))))
            upper = min(self._draw_buffer.height - 1, int(math.ceil(max(y for x, y in points))))
            for yi in range(lower, upper + 1):
                crossings = []
                py = yi + 0.5
                for k, (x1, y1) in enumerate(points):
                    x2, y2 = points[(k + 1) % count]
                    if (y1 <= py < y2) or (y2 <= py < y1):
                        crossings.append(x1 + (py-y1)*(x2-x1)/(y2-y1))
                crossings.sort()
                for a, b in zip(crossings[::2], crossings[1::2]):
                    start = max(0, int(math.ceil(a)))
                    end = min(self._draw_buffer.width-1, int(math.floor(b)))
                    for xi in range(start, end+1):
                        self._draw_buffer.pixel(xi, yi, *tone)
        for k, (x1, y1) in enumerate(points):
            x2, y2 = points[(k+1) % count]
            self.line(x1, y1, x2, y2, color=self.foreground if border is None else border)

    def blit_buffer_command(self, action, number, *args):
        """Buffer grafico independiente de pantalla N/F/L, sin dependencias Qt."""
        number = int(number)
        if not 1 <= number <= 32:
            raise BasicError('BLIT: buffer fuera de rango (1-32)')
        action = action.upper()
        if action == 'CLOSE':
            if number not in self.blit_buffers:
                raise BasicError('BLIT CLOSE: buffer no definido')
            del self.blit_buffers[number]
            return
        if action == 'READ':
            x, y, width, height = map(int, args)
            source = self._draw_buffer
            if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > source.width or y + height > source.height:
                raise BasicError('BLIT READ: dimensiones fuera de pantalla')
            if number in self.blit_buffers:
                raise BasicError('BLIT READ: buffer ya existe')
            lines = [bytes(source.pixels[4 * ((y + j) * source.width + x):
                                         4 * ((y + j) * source.width + x + width)])
                     for j in range(height)]
            self.blit_buffers[number] = (width, height, b''.join(lines))
            return
        if action == 'WRITE':
            if number not in self.blit_buffers:
                raise BasicError('BLIT WRITE: buffer no definido')
            x, y = map(int, args[:2])
            width, height, rgba = self.blit_buffers[number]
            w, h = (width, height) if len(args) == 2 else tuple(map(int, args[2:]))
            if w <= 0 or h <= 0 or w > width or h > height:
                raise BasicError('BLIT WRITE: dimensiones invalidas')
            # El buffer almacenado puede ser mayor que la region a escribir.
            if (w, h) != (width, height):
                rgba = b''.join(rgba[j * width * 4:j * width * 4 + w * 4] for j in range(h))
            self._draw_buffer.paste_rgba(rgba, w, h, x, y)
            return
        raise BasicError(f'BLIT: accion desconocida: {action}')

    def blit_load_data(self, number, x, y, width, height, rgba):
        """Recibe bytes RGBA decodificados por la sesion, no por Qt."""
        number = int(number)
        if not 1 <= number <= 32:
            raise BasicError('BLIT LOAD: buffer fuera de rango')
        if number in self.blit_buffers:
            raise BasicError('BLIT LOAD: buffer ya existe')
        if width <= 0 or height <= 0 or len(rgba) != width * height * 4:
            raise BasicError('BLIT LOAD: imagen invalida')
        self.blit_buffers[number] = (width, height, bytes(rgba))

    @staticmethod
    def sprite_palette(index):
        index = int(index)
        return (255 if index & 8 else 0, ((index >> 1) & 3) * 85,
                255 if index & 1 else 0)

    def sprite_store(self, number, width, height, rgba, *, transparent=0, alphacut=20):
        number = int(number)
        if not 1 <= number <= 64 or number in self.sprite_buffers:
            raise BasicError('SPRITE: numero ocupado o invalido')
        if not 0 < width < self.framebuffer.width or not 0 < height < self.framebuffer.height:
            raise BasicError('SPRITE: dimensiones invalidas')
        if len(rgba) != width * height * 4:
            raise BasicError('SPRITE: longitud de imagen invalida')
        data = bytearray(len(rgba))
        replacement = self.sprite_palette(transparent)
        for off in range(0, len(rgba), 4):
            if rgba[off + 3] < alphacut:
                color = replacement
            else:
                # RGB888 -> RGB121 (nibbles, dos pixeles por byte en hardware).
                r,g,b = rgba[off:off + 3]
                color = (255 if r >= 128 else 0,
                         min(3, (g * 3 + 127) // 255) * 85,
                         255 if b >= 128 else 0)
            data[off:off + 4] = bytes((*color, 255))
        self.sprite_buffers[number] = (int(width), int(height), bytes(data))

    def _sprite_capture(self, surface, x, y, width, height):
        """Captura RGBA con clipping. Se usa al salvar el fondo tapado."""
        data = bytearray(width * height * 4)
        for j in range(height):
            py = y + j
            if not 0 <= py < surface.height:
                continue
            left, right = max(0, x), min(surface.width, x + width)
            if left >= right:
                continue
            src = (py * surface.width + left) * 4
            dest = (j * width + left - x) * 4
            data[dest:dest + (right-left)*4] = surface.pixels[src:src+(right-left)*4]
        return bytes(data)

    def _sprite_paste(self, surface, x, y, width, height, rgba, options=0):
        """Copia sprite con transparencia RGB121 y espejos, sin tocar zonas fuera del LCD."""
        key = self.sprite_palette(self.sprite_transparent)
        for j in range(height):
            dy = y+j
            if not 0 <= dy < surface.height:
                continue
            sy = height-1-j if options & 2 else j
            for i in range(width):
                dx = x+i
                if not 0 <= dx < surface.width:
                    continue
                sx = width-1-i if options & 1 else i
                src = (sy*width+sx)*4
                pix = rgba[src:src+4]
                # SHOW: bit 2 obliga a mostrar negro, aunque sea el color transparente.
                if not (options & 4) and tuple(pix[:3]) == key:
                    continue
                dst = (dy*surface.width+dx)*4
                surface.pixels[dst:dst+4] = pix

    def _sprite_remove(self, number, safe=False):
        if number not in self.sprite_visible:
            raise BasicError('SPRITE HIDE: sprite no visible')
        # SAFE desmonta los sprites superiores del mismo plano y los repinta
        # tras restituir el fondo del sprite solicitado.
        index = self.sprite_order.index(number)
        info = self.sprite_visible[number]
        upper = [n for n in self.sprite_order[index+1:]
                 if self.sprite_visible[n][0] == info[0]] if safe else []
        for n in reversed(upper):
            self._sprite_erase(n)
        self._sprite_erase(number)
        self.sprite_order.remove(number)
        del self.sprite_visible[number]
        for n in upper:
            self._sprite_redraw(n)

    def _sprite_erase(self, number):
        target, x, y, layer, options, saved = self.sprite_visible[number]
        width, height, _ = self.sprite_buffers[number]
        self._sprite_restore(self.buffers[target], x, y, width, height, saved)

    @staticmethod
    def _sprite_restore(surface, x, y, width, height, rgba):
        for j in range(height):
            py = y+j
            if not 0 <= py < surface.height:
                continue
            left,right = max(0,x), min(surface.width,x+width)
            if left >= right:
                continue
            src = (j*width+left-x)*4
            dest = (py*surface.width+left)*4
            surface.pixels[dest:dest+(right-left)*4] = rgba[src:src+(right-left)*4]

    def _sprite_redraw(self, number):
        target,x,y,layer,options,_ = self.sprite_visible[number]
        width,height,rgba = self.sprite_buffers[number]
        surface = self.buffers[target]
        saved = self._sprite_capture(surface,x,y,width,height)
        self.sprite_visible[number] = (target,x,y,layer,options,saved)
        self._sprite_paste(surface,x,y,width,height,rgba,options)

    def _sprite_show(self, number, x, y, layer, options=0, safe=False, ontop=False):
        if number not in self.sprite_buffers:
            raise BasicError('SPRITE SHOW: sprite no definido')
        if not 0 <= layer <= 8 or not 0 <= options <= 7:
            raise BasicError('SPRITE SHOW: capa u opciones invalidas')
        target = self.write_target
        if number in self.sprite_visible:
            old = self.sprite_visible[number]
            if old[0] != target:
                raise BasicError('SPRITE SHOW: no se puede mover a otro framebuffer')
            index = self.sprite_order.index(number)
            # La variante SAFE conserva el orden de pintado; ontop la sube.
            upper = [n for n in self.sprite_order[index+1:]
                     if self.sprite_visible[n][0] == target]
            for n in reversed(upper):
                self._sprite_erase(n)
            self._sprite_erase(number)
            if safe and not ontop:
                self.sprite_visible[number] = (target,int(x),int(y),int(layer),int(options),b'')
                self._sprite_redraw(number)
                for n in upper:
                    self._sprite_redraw(n)
                return
            self.sprite_order.remove(number)
            del self.sprite_visible[number]
            for n in upper:
                self._sprite_redraw(n)
        width,height,rgba = self.sprite_buffers[number]
        surface = self.buffers[target]
        saved = self._sprite_capture(surface,int(x),int(y),width,height)
        self.sprite_visible[number] = (target,int(x),int(y),int(layer),int(options),saved)
        self.sprite_order.append(number)
        self._sprite_paste(surface,int(x),int(y),width,height,rgba,int(options))

    def sprite_command(self, action, *args):
        action = str(action).upper()
        if action == 'TRANSPARENT':
            self.sprite_transparent = int(args[0])
            return
        if action == 'CLOSE_ALL':
            # CLOSE no restaura la pantalla, pero descarta los fondos pendientes.
            self.sprite_buffers.clear()
            self.sprite_visible.clear()
            self.sprite_order.clear()
            return
        if action in ('SHOW', 'SHOW_SAFE'):
            number,x,y,layer = map(int,args[:4])
            options = int(args[4]) if len(args) > 4 else 0
            ontop = int(args[5]) if len(args) > 5 else 0
            if ontop not in (0,1):
                raise BasicError('SPRITE SHOW SAFE: ontop invalido')
            self._sprite_show(number,x,y,layer,options,
                              safe=action == 'SHOW_SAFE', ontop=bool(ontop))
            return
        if action in ('HIDE','HIDE_SAFE'):
            self._sprite_remove(int(args[0]),safe=action == 'HIDE_SAFE')
            return
        if action == 'SWAP':
            n1,n2 = int(args[0]),int(args[1])
            orientation = int(args[2]) if len(args)>2 else 0
            if n1 not in self.sprite_visible or n2 not in self.sprite_buffers:
                raise BasicError('SPRITE SWAP: sprite no definido o no visible')
            if n1 == n2:
                return
            if n2 in self.sprite_visible:
                raise BasicError('SPRITE SWAP: sustituto ya visible')
            if self.sprite_buffers[n1][:2] != self.sprite_buffers[n2][:2]:
                raise BasicError('SPRITE SWAP: dimensiones distintas')
            if not 0 <= orientation <= 7:
                raise BasicError('SPRITE SWAP: orientacion invalida')
            idx = self.sprite_order.index(n1)
            target,x,y,layer,old_options,_ = self.sprite_visible[n1]
            upper = [n for n in self.sprite_order[idx+1:]
                     if self.sprite_visible[n][0] == target]
            for n in reversed(upper):
                self._sprite_erase(n)
            self._sprite_erase(n1)
            del self.sprite_visible[n1]
            self.sprite_order[idx] = n2
            self.sprite_visible[n2] = (target,x,y,layer,orientation,b'')
            self._sprite_redraw(n2)
            for n in upper:
                self._sprite_redraw(n)
            return
        number = int(args[0])
        if action == 'CLOSE':
            if number not in self.sprite_buffers:
                raise BasicError('SPRITE CLOSE: sprite no definido')
            # CLOSE libera el recurso sin modificar lo que ya se dibujo.
            if number in self.sprite_visible:
                self.sprite_order.remove(number)
                del self.sprite_visible[number]
            del self.sprite_buffers[number]
            return
        if action == 'READ':
            x,y,width,height = map(int,args[1:])
            surface = self._draw_buffer
            if (x < 0 or y < 0 or width <= 0 or height <= 0 or
                    x + width > surface.width or y + height > surface.height):
                raise BasicError('SPRITE READ: region fuera de pantalla')
            rgba = b''.join(bytes(surface.pixels[((y+j)*surface.width+x)*4:
                                                   ((y+j)*surface.width+x+width)*4])
                            for j in range(height))
            self.sprite_store(number,width,height,rgba)
            return
        if action == 'WRITE':
            if number not in self.sprite_buffers:
                raise BasicError('SPRITE WRITE: sprite no definido')
            x,y = map(int,args[1:3])
            mode = int(args[3]) if len(args) == 4 else 4
            if mode < 0 or mode > 7:
                raise BasicError('SPRITE WRITE: modo invalido')
            width,height,rgba = self.sprite_buffers[number]
            key = self.sprite_palette(self.sprite_transparent)
            target = self._draw_buffer
            for yy in range(height):
                dy = y + yy
                if not 0 <= dy < target.height: continue
                sy = height - 1 - yy if mode & 2 else yy
                for xx in range(width):
                    dx = x + xx
                    if not 0 <= dx < target.width: continue
                    sx = width - 1 - xx if mode & 1 else xx
                    pos = (sy*width + sx)*4
                    pixel = rgba[pos:pos+4]
                    if (mode & 4) and tuple(pixel[:3]) == key:
                        continue
                    dest = (dy*target.width+dx)*4
                    target.pixels[dest:dest+4] = pixel
            return
        raise BasicError('SPRITE: operacion desconocida')

    def graphics(self, command):
        op,*args=command
        if op == 'sprite_command':
            self.sprite_command(*args)
            return
        if op == 'sprite_load_data':
            action, number, width, height, rgba, *opts = args
            transparent = int(opts[0]) if opts else 0
            alphacut = int(opts[1]) if len(opts) > 1 else 20
            self.sprite_store(number, width, height, rgba, transparent=transparent, alphacut=alphacut)
            return
        if op == 'blit_buffer':
            self.blit_buffer_command(*args)
            return
        if op == 'blit_load_data':
            self.blit_load_data(*args)
            return
        if op == 'framebuffer':
            self.framebuffer_command(*args)
            return
        if op == 'load_raster':
            if len(args) != 7:
                raise BasicError('LOAD JPG: datos graficos incorrectos')
            fmt, filename, x, y, width, height, rgba = args
            self._draw_buffer.paste_rgba(rgba, width, height, x, y,
                                         skip_transparent=(fmt == 'PNG'))
            return
        if op == 'definefont':
            if len(args) != 5:
                raise BasicError('DEFINEFONT: datos incorrectos')
            number, width, height, first, payload = args
            self.fonts[int(number)] = (int(width), int(height), int(first), bytes(payload))
            return
        if op == 'font':
            if not 1 <= len(args) <= 2:
                raise BasicError('FONT: argumentos')
            number = int(args[0])
            scale = int(args[1]) if len(args) > 1 else 1
            self._font_info(number)
            if not 1 <= scale <= 8:
                raise BasicError('FONT: escala fuera de rango')
            self.current_font, self.font_scale = number, scale
            self.col = self.row = 0
            return
        if op=='cls': self.cls(args[0]); return
        if op=='color':
            self.foreground,self.background=map(int,args)
            return
        if op=='rbox':
            if not 4 <= len(args) <= 7:
                raise BasicError('RBOX: argumentos')
            self.rbox(*args)
            return
        if op=='polygon':
            if not 3 <= len(args) <= 5:
                raise BasicError('POLYGON: argumentos')
            self.polygon(*args)
            return
        if op=='print_at':
            x, y, text, mode = args
            cw, ch = self._font_info(self.current_font)
            yy = self.row * ch * self.font_scale if y is None else int(y)
            if int(mode) not in (0, 1, 2):
                raise BasicError('PRINT @: modo de video no disponible')
            if int(mode) == 2:
                # PicoMite: m=2 invierte letras y fondo.
                self.text(x, yy, text, color=self.background, background=self.foreground)
            else:
                self.text(x, yy, text, background=-1 if int(mode) == 1 else None)
            return
        if op=='blit':
            if len(args) != 6: raise BasicError('BLIT: se esperan seis argumentos')
            self._draw_buffer.blit(*args)
            return
        if op=='pixel':
            if len(args) not in (2,3): raise BasicError('PIXEL: argumentos')
            self._draw_buffer.pixel(int(args[0]),int(args[1]),*rgb(args[2] if len(args)>2 else self.foreground))
            return
        if op=='line':
            if len(args) < 4 or len(args)>6: raise BasicError('LINE: argumentos')
            self.line(*args[:4],color=args[5] if len(args)>5 else None,thickness=args[4] if len(args)>4 else 1)
            return
        if op=='box': self.box(*args); return
        if op=='circle': self.circle(*args); return
        if op=='text': self.text(*args); return
        raise BasicError(f'Operacion grafica no disponible: {op}')
