# -*- coding: utf-8 -*-
"""Valida uma rampa de cores para grafico em fundo escuro.
Checa: contraste vs fundo, distincia entre pares (visao normal) e o mesmo
sob deuteranopia e protanopia. Sem chute -- numero."""
import math, sys, itertools

BG = "#0A0D11"

def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))
def lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
def lum(h):
    r,g,b = [lin(c) for c in hex2rgb(h)]
    return 0.2126*r + 0.7152*g + 0.0722*b
def contraste(a,b):
    la,lb = lum(a),lum(b); hi,lo = max(la,lb),min(la,lb)
    return (hi+0.05)/(lo+0.05)
def rgb2xyz(rgb):
    r,g,b = [lin(c) for c in rgb]
    return (0.4124*r+0.3576*g+0.1805*b, 0.2126*r+0.7152*g+0.0722*b, 0.0193*r+0.1192*g+0.9505*b)
def f(t): return t**(1/3.) if t > 0.008856 else 7.787*t + 16/116.
def xyz2lab(x,y,z):
    xn,yn,zn = 0.95047,1.0,1.08883
    fx,fy,fz = f(x/xn), f(y/yn), f(z/zn)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))
def lab(h): return xyz2lab(*rgb2xyz(hex2rgb(h)))
def de(a,b):
    la,lb = lab(a),lab(b)
    return math.sqrt(sum((x-y)**2 for x,y in zip(la,lb)))

# Simulacao de CVD (Vienot 1999) sobre LMS
def cvd(h, tipo):
    r,g,b = [lin(c) for c in hex2rgb(h)]
    L = 17.8824*r + 43.5161*g + 4.11935*b
    M = 3.45565*r + 27.1554*g + 3.86714*b
    S = 0.0299566*r + 0.184309*g + 1.46709*b
    if tipo == "protan": L2, M2, S2 = 2.02344*M - 2.52581*S, M, S
    else:                L2, M2, S2 = L, 0.494207*L + 1.24827*S, S
    r2 =  0.080944*L2 - 0.130504*M2 + 0.116721*S2
    g2 = -0.0102485*L2 + 0.0540194*M2 - 0.113615*S2
    b2 = -0.000365294*L2 - 0.00412163*M2 + 0.693513*S2
    def out(c):
        c = max(0.0, min(1.0, c))
        c = 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055
        return "%02X" % int(round(max(0,min(1,c))*255))
    return "#" + out(r2)+out(g2)+out(b2)

def valida(rampa, nome=""):
    print("=== %s ===" % nome)
    ok = True
    for c in rampa:
        k = contraste(c, BG); L = lab(c)[0]
        flag = "" if k >= 3.0 else "  <-- CONTRASTE BAIXO"
        if k < 3.0: ok = False
        print("  %s  contraste %.2f  L* %.1f%s" % (c, k, L, flag))
    piores = []
    for a,b in itertools.combinations(rampa,2):
        d  = de(a,b)
        dp = de(cvd(a,"protan"), cvd(b,"protan"))
        dd = de(cvd(a,"deutan"), cvd(b,"deutan"))
        piores.append((min(dp,dd), d, a, b))
    piores.sort()
    normal_min = min(de(a,b) for a,b in itertools.combinations(rampa,2))
    print("  menor dE visao normal: %.1f (piso 15)%s" % (normal_min, "" if normal_min>=15 else "  <-- BAIXO"))
    if normal_min < 15: ok = False
    print("  3 piores pares sob daltonismo (alvo >= 8):")
    for m,d,a,b in piores[:3]:
        print("     %s x %s  CVD dE %.1f  normal %.1f%s" % (a,b,m,d,"" if m>=8 else "   <-- BAIXO"))
    if piores[0][0] < 8: ok = False
    print("  RESULTADO:", "PASSA" if ok else "REPROVA")
    print()
    return ok

# ---- gerador em LCh: util para propor rampas novas ----
def lch2hex(L,C,h):
    hr = math.radians(h); a,b = C*math.cos(hr), C*math.sin(hr)
    fy = (L+16)/116.; fx = fy + a/500.; fz = fy - b/200.
    def inv(t): return t**3 if t**3 > 0.008856 else (t - 16/116.)/7.787
    xn,yn,zn = 0.95047,1.0,1.08883
    x,y,z = inv(fx)*xn, inv(fy)*yn, inv(fz)*zn
    r =  3.2406*x - 1.5372*y - 0.4986*z
    g = -0.9689*x + 1.8758*y + 0.0415*z
    bb =  0.0557*x - 0.2040*y + 1.0570*z
    def out(c):
        c = max(0.0, min(1.0, c))
        c = 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055
        return "%02X" % int(round(max(0,min(1,c))*255))
    return "#" + out(r)+out(g)+out(bb)

if __name__ == "__main__":
    # A rampa que esta no ar (RAMPA no bloco <contas> do index.html).
    ATUAL = ["#3BD8B6", "#D0A553", "#3A9BEB", "#C25F99", "#00C0D8", "#7D5EAD"]
    valida(ATUAL, "rampa das contas (em uso)")
    print("Mexeu na RAMPA do index.html? rode este script e confira o PASSA.")
    print("Lembrete: rampa de luminancia IGUAL fica bonita e REPROVA -- sob")
    print("deuteranopia o matiz colapsa e so a diferenca de L* separa as cores.")

# ---- gerador em LCh: mesma luminancia, croma menor, matizes escolhidos ----
def lch2hex(L,C,h):
    hr = math.radians(h); a,b = C*math.cos(hr), C*math.sin(hr)
    fy = (L+16)/116.; fx = fy + a/500.; fz = fy - b/200.
    def inv(t): return t**3 if t**3 > 0.008856 else (t - 16/116.)/7.787
    xn,yn,zn = 0.95047,1.0,1.08883
    x,y,z = inv(fx)*xn, inv(fy)*yn, inv(fz)*zn
    r =  3.2406*x - 1.5372*y - 0.4986*z
    g = -0.9689*x + 1.8758*y + 0.0415*z
    bb =  0.0557*x - 0.2040*y + 1.0570*z
    def out(c):
        c = max(0.0, min(1.0, c))
        c = 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4)) - 0.055
        return "%02X" % int(round(max(0,min(1,c))*255))
    return "#" + out(r)+out(g)+out(bb)

def gerar(L, C, hues): return [lch2hex(L,C,h) for h in hues]
