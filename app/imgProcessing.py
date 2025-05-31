from PIL import Image
import numpy as np

__colorList = {
    "black": (5, 19, 29),
    "dark_bluish_grey": (108, 110, 104),
    "light_bluish_grey": (160, 165, 169),
    "white": (255, 255, 255)
}

def __find_closest_color(targetColor, colorList):
    closestColor = min(colorList, key=lambda colorName: np.linalg.norm(np.array(colorList[colorName]) - np.array(targetColor)))
    return closestColor

def convert_image(imagePath):
    newImage = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    lego = []
    itemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white": 0}

    img = Image.open(imagePath)
    img = img.resize((32,32), Image.NEAREST)
    # img = img.convert("L")
    img = img.convert("RGBA")

    width, height = img.size

    imgData = img.load()

    for y in range(height):
        for x in range(width):
            pixelColor = imgData[x, y]
            if not pixelColor == (0, 0, 0, 0):
                r, g, b, _ = pixelColor
                gray = int(0.299 * r + 0.587 * g +0.114*b) # graustufen umrechnung bild modus "L"
                closestColor = __find_closest_color(gray, __colorList)
                # lego[f"{x},{31-y}"] = closestColor
                lego.append([(f"{x},{31-y}"), closestColor])
                itemCount[closestColor] += 1
                newImage.putpixel((x, y), __colorList[closestColor])

    return newImage, lego, itemCount

if __name__ == "__main__":
    imagePath = "pigeon.png"
    newImage, lego, itemcount = convert_image(imagePath)
    print(lego)
    # newImage.save('3.png')