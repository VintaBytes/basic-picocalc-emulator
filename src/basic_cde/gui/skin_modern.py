"""New photographic skins. Coordinate models are independent of Qt."""
from importlib import resources
from pathlib import Path
from basic_cde.gui.skin import SkinLayout
from basic_cde.gui.skin_keys import KEY_ZONES_VERTICAL, KeyZone

# (PNG width, height), (square LCD x,y,size), (stop button x,y,size)
MODERN_SKINS = {
    'horizontal': ((1774,887), (98,101,700), (1660,35,26)),
    'vertical': ((954,1649), (88,99,710), (869,39,27)),
    'large': ((1203,1216), (47,74,1075), (1114,35,28)),
    'compact': ((1164,1216), (100,125,980), (1018,52,29)),
}
KEY_TRANSFORMS = {
    'vertical': (1.253,1.225,-54,-25),
    'horizontal': (1.29,1.23,770,-681),
}

def modern_skin_asset_path(mode):
    if mode not in MODERN_SKINS:
        raise ValueError(mode)
    return str(Path(resources.files('basic_cde.gui')/'assets'/f'picocalc-modern-{mode}.png'))

def modern_skin_layout(mode):
    photo, (x,y,aperture), _ = MODERN_SKINS[mode]
    side = 640 if mode == 'large' else 320
    scale = side/aperture
    return SkinLayout(round(photo[0]*scale),round(photo[1]*scale),
                      round(x*scale),round(y*scale),side,mode)

def stop_button_rect(mode):
    _,(_,_,aperture),(x,y,size) = MODERN_SKINS[mode]
    k = (640 if mode=='large' else 320)/aperture
    return round(x*k),round(y*k),max(13,round(size*k))



# Zonas de pulsación de las crucetas, en píxeles de cada fotografía.
# Para estas cuatro teclas no se usa la transformación del teclado antiguo.
# Permite mejorar y probar cada dirección por separado.
ARROW_POLYGONS = {
    'vertical': {
        'Up': ((127, 838), (213, 838), (235, 857), (173, 916), (110, 857)),
        'Left': ((92, 881), (127, 881), (161, 927), (127, 975), (92, 975)),
        'Right': ((217, 881), (251, 881), (251, 975), (217, 975), (185, 927)),
        'Down': ((126, 962), (173, 933), (221, 962), (221, 999), (126, 999)),
    },
    'horizontal': {
        'Up': ((969, 185), (1072, 185), (1081, 197), (1018, 248), (958, 197)),
        'Left': ((944, 209), (976, 209), (1000, 254), (977, 297), (944, 297)),
        'Right': ((1052, 210), (1090, 210), (1090, 296), (1052, 296), (1031, 255)),
        'Down': ((972, 282), (1018, 258), (1066, 282), (1068, 333), (972, 333)),
    },
}

def modern_key_zones(mode):
    if mode not in KEY_TRANSFORMS:
        return ()
    sx,sy,ox,oy = KEY_TRANSFORMS[mode]
    result=[]
    for zone in KEY_ZONES_VERTICAL:
        if zone.name in ARROW_POLYGONS.get(mode, {}):
            poly = ARROW_POLYGONS[mode][zone.name]
            xs, ys = zip(*poly)
            result.append(KeyZone(zone.name, min(xs), min(ys),
                                  max(xs)-min(xs), max(ys)-min(ys), poly))
            continue
        poly=tuple((round(px*sx+ox),round(py*sy+oy)) for px,py in zone.polygon)
        result.append(KeyZone(zone.name,round(zone.x*sx+ox),round(zone.y*sy+oy),
                              round(zone.width*sx),round(zone.height*sy),poly))
    return tuple(result)

def modern_key_at(x,y,mode):
    for zone in modern_key_zones(mode):
        if zone.contains(x,y):
            return zone.name
    return None
