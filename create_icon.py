from PIL import Image, ImageDraw, ImageFont

# Create a 256x256 image with a graduation cap icon
img = Image.new('RGB', (256, 256), color='#007bff')
draw = ImageDraw.Draw(img)

# Draw a simple graduation cap shape
# Cap top (rectangle)
draw.rectangle([60, 80, 196, 110], fill='#ffffff')

# Cap base (trapezoid approximation)
draw.polygon([80, 110, 176, 110, 196, 140, 60, 140], fill='#ffffff')

# Tassel
draw.ellipse([118, 70, 138, 90], fill='#ffd700')
draw.rectangle([125, 90, 131, 120], fill='#ffd700')
draw.ellipse([120, 115, 136, 131], fill='#ffd700')

# Text
try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

text = "ZEB"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_x = (256 - text_width) // 2
draw.text((text_x, 160), text, fill='#ffffff', font=font)

# Save as ICO
img.save('app_icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
print("✅ Icon created: app_icon.ico")