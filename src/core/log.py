__verbose = False
__verbose_level = 1

debug = {
    0 : "[s]", # server
    1 : "[i]", # info
    2 : "[W]", # warn
    3 : "[*]", # error
    4 : "[**]" # catastrophic error
}

def log(*args, level=None, sep=" "):
    """
    Aceita múltiplos argumentos assim como o print().
    Exemplo: log("Variável", x, "carregada com sucesso", level=2)
    """
    if len(args) == 2 and isinstance(args[1], int) and level is None:
        message = str(args[0])
        lvl = args[1]
    else:
        message = sep.join(map(str, args))
        lvl = level if level is not None else 1

    prefix = debug.get(lvl, "[?]")

    if lvl == 0 or lvl == 4:
        print(f"{prefix} {message}")
        return

    if __verbose and __verbose_level >= lvl:
        print(f"{prefix} {message}")


def setVerbose(is_verbose : bool):
    global __verbose
    __verbose = is_verbose

def setLevel(verbose_level : int):
    global __verbose_level
    __verbose_level = verbose_level