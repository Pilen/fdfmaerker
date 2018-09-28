
import collections
import re
import itertools
from pathlib import Path
from pprint import pprint
import shutil
import tempfile
from creole import creole2html
from flask import Flask, Blueprint, render_template
import PIL
import PIL.Image
# from PIL import Image as PIL_Image
app = Flask(__name__, static_url_path="/")

errors = []
def error(*args, **kwargs):
    error = kwargs.get("sep", " ").join(args)
    print(error, **kwargs)
    errors.append(error)

macros = {}
def macro(function):
    macros[function.__name__] = function
    return function

def parse_arguments(text, sep):
    text = text.strip().lstrip(sep).strip()
    return [x.strip() for x in text.split(sep)]

def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)



@macro
def redaktør(text, state):
    name, email = parse_arguments(text, "|")
    state["redaktør"] = {"name": name, "email": email}
    return ""

@macro
def mærke(text, state):
    mærketitel, mærkecanonical, *_ = parse_arguments(text, "|")
    state["mærketitel"] = mærketitel
    state["mærkecanonical"] = mærkecanonical
    return ""

@macro
def oplevelse(text, state):
    oplevelsetitel, *_ = parse_arguments(text, "|")
    state["oplevelsetitel"] = oplevelsetitel
    return ""

@macro
def icon(text, state):
    return "<img class='icon' src='{}'/>".format(state["icon"].url)

@macro
def ikon(*args, **kwargs):
    return icon(*args, **kwargs)

@macro
def niveau(text, state):
    if "niveau" not in state:
        state["niveau"] = []
    state["niveau"].append(text)
    return ""


class Image:
    def __init__(self, path, url=None, resize=None):
        if path and url:
            url = Path("/") / url / path.name
        else:
            url = Path("/static/missing-image.png")
        if not path:
            resize = None
        if resize:
            url = url.with_suffix(".{}x{}.png".format(*resize))
        self.path = path
        self.name = path.name if path else None
        self.resize = resize
        self.url = url

    def copy_into(self, destination):
        resize = self.resize
        # shutil.copy(mærke["path"] / mærke["icon"].name, mærke_dir / mærke["icon"].name)
        if not self.path:
            return

        url = str(self.url)
        if url.startswith("/"):
            url = url[1:]
        if not resize:
            shutil.copy(self.path, destination / url)
        else:
            print("Copying image resize")
            img = PIL.Image.open(self.path)
            # img.thumbnail(resize)
            img = thumbnail(img, resize)
            print("saving")
            img.save(destination / url)
            print("done")

def thumbnail(img, size, align_x=0.5, align_y=0.5):
    width, height = size

    aspect_ratio = width / height
    im_aspect_ratio = img.width / img.height
    if im_aspect_ratio > aspect_ratio:
        new_width = int(img.height * aspect_ratio)
        new_height = img.height
    elif im_aspect_ratio < aspect_ratio:
        new_width = img.width
        new_height = int(img.width / aspect_ratio)
    else:
        new_width = img.width
        new_height = img.height
    # img = img.crop((align_x * (img.width - new_width),
    #                 align_y * (img.height - new_height),
    #                 align_x * (img.width - new_width) + new_width,
    #                 align_y * (img.height - new_height) + new_height))
    # img.resize(size)
    # return img
    print("resize", (img.width, img.height),
          size,
          (align_x * (img.width - new_width),
           align_y * (img.height - new_height),
           new_width,
           new_height))
    return img.resize(size,
                      resample=PIL.Image.LANCZOS,
                      box=(align_x * (img.width - new_width),
                           align_y * (img.height - new_height),
                           new_width,
                           new_height))





def convert(text, state={}, where=None):
    substitutions = []
    def substitute(match):
        name, args = match.groups()
        macro = macros.get(name.lower(), None)
        if not macro:
            msg = "[Error: Unknown macro {}]".format(name)
            error("Unknown macro {} in {}".format(name, where))
            return "[Error: Unknown macro {}]".format(name)
        n = len(substitutions)
        substitutions.append(macro(args.strip(), state) or "")
        return "%%%%%%%%{}%%%%%%%%".format(n)
    def reinsert(match):
        n = match.groups()[0]
        return substitutions[int(n)]
    macro_re = "<<([^> ]+)([^>]*)>>"
    text = re.sub("^({})\n".format(macro_re), "\\1", text, flags=re.MULTILINE)
    processed = re.sub(macro_re, substitute, text)
    html = creole2html(processed)
    return re.sub("%%%%%%%%([0-9]+)%%%%%%%%", reinsert, html)

def read_file(file, state):
    if file.is_file():
        try:
            converted = convert(file.read_text(), state, file)
        except Exception as e:
            error("There was an error converting {}".format(str(file)))
            raise
        if converted:
            return "<div>{}</div><hr/>".format(converted)
    print("WARNING: not such file: {}".format(file))
    return None

def get_mærke(path, state):
    if not path.exists():
        raise Exception("Not found: {}".format(path))
    state["path"] = path
    state["intro"] = read_file(path / "mærke.txt", state) or ""
    state["viden"] = read_file(path / "viden.txt", state) or ""
    state["url"] = urlify(state["mærkecanonical"])
    icons = list(path.glob("ikon.*"))
    state["icon"] = Image(icons[0] if icons else None, state["url"], resize=(100, 100))
    state["oplevelser"] = [get_oplevelse(dir, state.new_child())
                           for dir in path.glob("*")
                           if dir.is_dir()]
    return state

def get_oplevelse(path, state):
    state["path"] = path
    state["url"] = state["url"] + "/" + urlify(path.name)
    state["beskrivelse"] = read_file(path / "oplevelse.txt", state) or ""
    state["viden"] = read_file(path / "viden.txt", state) or ""
    images = path.glob("*[.jpg,.jpeg,.png]")
    images = [Image(image, state["url"], resize=(800, 500)) for image in images] or [Image(None, None)]
    state["images"] = images
    state["thumb"] = Image(images[0].path, state["url"], resize=(150, 100))
    return state

# def render_template(*args, **kwargs):
    # return "BLA BLA BLA"

def urlify(raw):
    match = re.match("([a-zA-Z]) *- *(.*)", raw)
    if match:
        letter, rest = match.groups()
        if rest:
            url = rest
        else:
            url = letter
    else:
        url = raw
    return re.sub("[^a-zæøå\-_]", "",
                  url.lower().strip().replace(" ", "_").replace("/", "_"))


def build_website(mærker, destination):
    destination.mkdir(parents=True, exist_ok=True)
    mærker.sort(key=lambda mærke: mærke["mærketitel"])
    for mærke in mærker:
        try:
            mærke_dir = destination / mærke["url"]
            mærke_dir.mkdir()
            mærke_file = mærke_dir / "index.html"
            mærke_file.write_text(render_template("mærke.html", mærke=mærke))
            mærke["icon"].copy_into(destination)
            oplevelser = mærke["oplevelser"]
            oplevelser.sort(key=lambda oplevelse: oplevelse["oplevelsetitel"])
            for oplevelse in oplevelser:
                try:
                    oplevelse_dir = destination / oplevelse["url"]
                    oplevelse_dir.mkdir()
                    oplevelse["thumb"].copy_into(destination)
                    for image in oplevelse["images"]:
                        image.copy_into(destination)
                    oplevelse_file = oplevelse_dir / "index.html"
                    oplevelse_file.write_text(render_template("oplevelse.html", mærke=mærke, oplevelse=oplevelse))
                except Exception as e:
                    error("Failed to build oplevelse {}".format(oplevelse))
                    raise
        except Exception as e:
            error("Failed to build mærke".format(mærke))
            raise
    index = render_template("frontpage.html", mærker=mærker)
    index_file = destination / "index.html"
    index_file.write_text(index)
    shutil.copytree(app.static_folder, destination / "static")





def build():
    try:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path("content")
            tmp = Path(tmp)
            source = Path("raw3")
            state = collections.ChainMap()
            mærker = [get_mærke(path, state.new_child())
                      for path in source.glob("*")
                      if path.is_dir()]
            # mærker = [get_mærke(Path("raw/testmærke"), state.new_child())]
            # mærker = [get_mærke(Path("raw2/bålaktivitet"), state.new_child())]
            # mærker = [get_mærke(Path("raw2/vandre"), state.new_child())]
            # pprint(mærker[0])
            build_website(mærker, tmp)
            shutil.rmtree(str(destination), ignore_errors=True)
            shutil.copytree(tmp, destination)
    except Exception as e:
        error("Failed to build website")
        raise

def main():
    with app.app_context():
        build()



if __name__ == "__main__":
    main()



# Todo: brug titler til url (final mapper)
# Todo: kig på brug af logo/farver/font
# Todo: Fejl beskeder
