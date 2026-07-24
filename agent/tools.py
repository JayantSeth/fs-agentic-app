import os

def list_files_and_folders(directory_path: str) -> str:
    """
    Get list of files and folders with size information in a given directory

    Args:
        directory_path: directory path to list the files from
    
    Returns
        Name, Size & is_file ( true for files) of all files in the directory_path
    """
    print(f"Directory path: {directory_path}")
    try:
        files = ""
        with os.scandir(directory_path) as entries:
            for entry in entries:
                files += f"Name: {entry.name}, Size: {entry.stat().st_size}, is_file: {entry.is_file()}\n"
        if len(files) == 0:
            return "No files or folders found"
        return files
    except Exception as e:
        return str(e)

def read_file(file_path: str, number_of_lines: int = -1) -> str:
    """
    Get Content of any given file

    Args:
        file_path: Path of the file which needs to be read
    Returns:
        Content of the file
    """
    try:
        with open(file_path, "r+") as f:
            lines = f.readlines(number_of_lines)
            if len(lines) == 0:
                return "No content found"
            if len(lines) > 100:
                raise "File is too large"
            return "\n".join(lines)
    except Exception as e:
        return str(e)

def delete_file(file_path: str) -> str:
    """
    Delete the files from local file system

    Args:
        file_path: Path of the file which needs to be deleted
    Returns:
        Delete confirmation or error
    """
    print(f"Deleting {file_path}")
    try:
        os.remove(file_path)
        return "File deleted successfully"
    except Exception as e:
        return str(e)

def get_env_value(var_name: str) -> str:
    """
    Get the value of environment variable

    Args:
        var_name: name of the environment variable
    
    Returns:
        Value of the mentioned environment variable
    """
    return os.getenv(var_name)