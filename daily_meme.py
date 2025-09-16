import os, io, base64, textwrap, requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

client = OpenAI(api_key=OPENAI_API_KEY)

def gen_meme_text(topic="технологии и продуктивность"):
    prompt = (
        "Сделай короткий мем-текст в формате:\n"
        "TITLE: <верхняя строка до 8 слов>\n"
        "BOTTOM: <нижняя строка до 8 слов>\n"
        "Правила: без токсичности, без брендов, русский, иронично, тема: " + topic
    )
    r = client.responses.create(model="gpt-4o-mini", input=prompt, temperature=0.8)
    txt = r.output_text
    top, bottom = "", ""
    for line in txt.splitlines():
        if line.upper().startswith("TITLE:"):
            top = line.split(":",1)[1].strip()
        if line.upper().startswith("BOTTOM:"):
            bottom = line.split(":",1)[1].strip()
    if not top:   top = "Когда дедлайн вчера"
    if not bottom: bottom = "а ТЗ ещё пишется"
    return top, bottom

def gen_base_image():
    r = client.images.generate(
        model="gpt-image-1",
        prompt="Забавная фотосток-сцена в офисе: человек за ноутбуком, лёгкая самоирония, без текста.",
        size="1024x1024",
        n=1,
    )
    b64 = r.data[0].b64_json
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

def draw_meme(base: Image.Image, top: str, bottom: str) -> Image.Image:
    W, H = base.size
    draw = ImageDraw.Draw(base)
    # шрифт с кириллицей; путь может отличаться в вашей ОС
    font_path_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for p in font_path_candidates:
        if os.path.exists(p):
            font_path = p
            break
    else:
        raise FileNotFoundError("Нужен TTF-шрифт с кириллицей (например, DejaVuSans-Bold.ttf).")
    font = ImageFont.truetype(font_path, size=64)

    def wrap(s): return "\n".join(textwrap.wrap(s.upper(), width=16))

    def draw_outline_text(x, y, text, anchor):
        # чёрная обводка
        for dx, dy in [(-3,-3),(-3,3),(3,-3),(3,3),(0,-3),(0,3),(-3,0),(3,0)]:
            draw.text((x+dx, y+dy), text, font=font, fill="black", anchor=anchor)
        # белый текст
        draw.text((x, y), text, font=font, fill="white", anchor=anchor)

    draw_outline_text(W/2, 40, wrap(top), "ma")       # верх
    draw_outline_text(W/2, H-40, wrap(bottom), "ms")  # низ
    return base

def send_photo_to_telegram(img: Image.Image, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    bio = io.BytesIO()
    img.save(bio, format="JPEG", quality=90)
    bio.seek(0)
    files = {"photo": ("meme.jpg", bio, "image/jpeg")}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    top, bottom = gen_meme_text()
    base = gen_base_image()
    meme = draw_meme(base, top, bottom)
    caption = f"*{top}*\n{bottom}\n\n#мем #технологии"
    res = send_photo_to_telegram(meme, caption)
    print("OK:", res.get("result", {}).get("message_id"))
