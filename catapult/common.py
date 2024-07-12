
def translate_file_path_between_os(file_path: str, origin_os: str, target_os: str) -> str:
    """
    Translates file path between OS.
    :param file_path: file path to translate
    :param origin_os: origin OS
    :param target_os: target OS
    """

    if origin_os == "nt" and target_os == "posix":
        return file_path.replace("\\", "/")
    elif origin_os == "posix" and target_os == "nt":
        return file_path.replace("/", "\\")

