"""TRAILER KARTLARI — her sahne karesine sinematik başlık + alt-anlatım bindir.
Letterbox (sinematik siyah bantlar) + alt-üçte-bir metin + ince başlık. Lore'dan
Türkçe. Çıktı: trailer/cardNN.png (1920x1080). ffmpeg sonra birleştirir.
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path("studio/autopilot/trailer")
F = "/c/Windows/Fonts/arialbd.ttf".replace("/c/", "C:/")
FR = "/c/Windows/Fonts/arial.ttf".replace("/c/", "C:/")

def font(sz, bold=True):
    return ImageFont.truetype(F if bold else FR, sz)

# (kare, üst-başlık, alt-anlatım(satırlar))
SCENES = [
    ("01_valley", "THORNIVY",
     ["Yıkılmış Fargoth diyarının", "uyuzla parçalanmış hududu"]),
    ("02_camp", "BRIAR HOLLOW",
     ["Soğuk, nemli, kırık güzellik.", "Kamp ateşi — biyomun en sıcak görseli."]),
    ("03_cabin", "KAMP DEMİRİ",
     ["Her seans buradan başlar:", "yeniden doğuş, toplanma, kit hazırlığı."]),
    ("04_castle", "FARGOTH TACI",
     ["Gotik başkent harabeleri.", "Crimson Spire'ın kızıl ışını her bölgeden görülür."]),
    ("05_lake", "ÇEK · DÖVÜŞ · GANİMET · TOPARLAN",
     ["Sağlam, ağır, okunabilir dövüş.", "Her ~15 dakikada anlamlı bir kazanç."]),
    ("06_rocks", "GÜZEL VE TEHLİKELİ",
     ["Sabırlı şiddetle bozulmuş doğal güzellik.", "Asla ucuz korku değil."]),
    ("07_danger", "BEŞ BÖLGE, TEK İNİŞ",
     ["Frostpine · Blackfen · Skarn · Fargoth.", "Her biri kendi fraksiyonu ve boss'uyla."]),
    ("08_aerial", "THORNIVY WARD OLARAK DÖN",
     ["Sürgün edilmiş kalkan-muhafızı.", "Diyarı bölge bölge temizle, ayini kır."]),
]

W, H = 1920, 1080
BAR = int(H * 0.12)  # letterbox yuksekligi

for sid, title, lines in SCENES:
    src = OUT / f"{sid}.png"
    if not src.exists():
        print("MISS", sid); continue
    im = Image.open(src).convert("RGB").resize((W, H))
    # hafif sinematik koyulastirma + kontrast (mood)
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    im = Image.blend(im, dark, 0.18)
    d = ImageDraw.Draw(im, "RGBA")
    # letterbox bantlar
    d.rectangle([0, 0, W, BAR], fill=(0, 0, 0, 255))
    d.rectangle([0, H - BAR, W, H], fill=(0, 0, 0, 255))
    # alt gradyan (metin okunsun)
    grad = Image.new("RGBA", (W, 320), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(320):
        a = int(150 * (i / 320))
        gd.line([(0, i), (W, i)], fill=(0, 0, 0, a))
    im.paste(grad, (0, H - BAR - 320), grad)
    d = ImageDraw.Draw(im, "RGBA")
    # baslik (alt-uctebir uzeri)
    tf = font(64, True)
    tw = d.textlength(title, font=tf)
    ty = H - BAR - 200
    # kurumus-kan kirmizi aksan cizgi
    d.rectangle([(W - tw) / 2 - 30, ty - 18, (W - tw) / 2 - 14, ty + 70], fill=(150, 30, 26, 255))
    d.text(((W - tw) / 2, ty), title, font=tf, fill=(232, 226, 214, 255))
    # anlatim satirlari
    sf = font(38, False)
    for i, ln in enumerate(lines):
        lw = d.textlength(ln, font=sf)
        d.text(((W - lw) / 2, ty + 88 + i * 48), ln, font=sf, fill=(196, 200, 205, 255))
    im.save(OUT / f"card_{sid}.png", quality=95)
    print("CARD", sid)

# kapanis karti (siyah + logo)
end = Image.new("RGB", (W, H), (6, 8, 9))
d = ImageDraw.Draw(end, "RGBA")
tf = font(96, True); t = "THORNIVY"
tw = d.textlength(t, font=tf)
d.text(((W - tw) / 2, H / 2 - 110), t, font=tf, fill=(232, 226, 214, 255))
sf = font(40, False); s = "Briar Hollow · Pre-Alpha Dikey Dilim"
sw = d.textlength(s, font=sf)
d.text(((W - sw) / 2, H / 2 + 10), s, font=sf, fill=(150, 30, 26, 255))
sf2 = font(30, False); s2 = "Güzel ve tehlikeli · Premium atmosfer · Önce his"
sw2 = d.textlength(s2, font=sf2)
d.text(((W - sw2) / 2, H / 2 + 80), s2, font=sf2, fill=(150, 154, 158, 255))
end.save(OUT / "card_09_end.png")
print("CARD end")
print("CARDS_DONE")
