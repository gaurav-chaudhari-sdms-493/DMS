import os
import subprocess
from PIL import Image

pub_dir = "/home/stark/JetBrainsProjects/DMS/frontend/public"
svg_path = os.path.join(pub_dir, "stark-dms-app-logo.svg")
src_512 = os.path.join(pub_dir, "stark-icon-512.png")

# 1. Render transparent 512x512 PNG using Chrome headless
chrome_cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--force-device-scale-factor=1",
    "--default-background-color=00000000",
    "--hide-scrollbars",
    f"--screenshot={src_512}",
    "--window-size=512,512",
    f"file://{svg_path}"
]
subprocess.run(chrome_cmd, check=True)

# 2. Open rendered 512x512 RGBA image
img = Image.open(src_512).convert("RGBA")

# Verify transparency
corners = [img.getpixel((0,0)), img.getpixel((511,0)), img.getpixel((0,511)), img.getpixel((511,511))]
print(f"Verified transparent corners: {corners}")

# 3. Generate all resized PNG icons with full alpha channel
sizes = [16, 32, 48, 64, 128, 180, 256, 512]

for sz in sizes:
    resized = img.resize((sz, sz), Image.Resampling.LANCZOS)
    out_path = os.path.join(pub_dir, f"stark-icon-{sz}.png")
    resized.save(out_path, "PNG")
    print(f"Saved transparent {out_path} ({sz}x{sz})")

# Main desktop app icon & favicons
img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
img_512.save(os.path.join(pub_dir, "stark-icon.png"), "PNG")
img_512.save(os.path.join(pub_dir, "icon.png"), "PNG")
print("Saved transparent stark-icon.png and icon.png (512x512)")

app_dir = "/home/stark/JetBrainsProjects/DMS/frontend/app"
if os.path.exists(app_dir):
    img_512.save(os.path.join(app_dir, "icon.png"), "PNG")
    print("Saved transparent app/icon.png")

img_180 = img.resize((180, 180), Image.Resampling.LANCZOS)
img_180.save(os.path.join(pub_dir, "apple-touch-icon.png"), "PNG")
print("Saved transparent apple-touch-icon.png (180x180)")

ico_sizes = [(16, 16), (32, 32), (48, 48)]
img.save(os.path.join(pub_dir, "favicon.ico"), format="ICO", sizes=ico_sizes)
print("Saved transparent favicon.ico (16, 32, 48)")
