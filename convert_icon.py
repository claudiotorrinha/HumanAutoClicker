from PIL import Image

<<<<<<< HEAD
img = Image.open("app_icon.png")
img.save("app_icon.ico", format="ICO", sizes=[(256, 256)])
=======
img = Image.open("app_icon.png").convert("RGBA")
img.save(
    "app_icon.ico",
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
)
>>>>>>> feature/refactor
print("Converted app_icon.png to app_icon.ico")
