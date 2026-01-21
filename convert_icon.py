from PIL import Image

img = Image.open("app_icon.png")
img.save("app_icon.ico", format="ICO", sizes=[(256, 256)])
print("Converted app_icon.png to app_icon.ico")
