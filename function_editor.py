import re
import sys

def modify_function(file_path, function_name, new_body):
    """
    Modyfikuje ciało funkcji w pliku Python bez potrzeby znajomości jej poprzedniej treści.
    
    Args:
        file_path: Ścieżka do pliku
        function_name: Nazwa funkcji do modyfikacji
        new_body: Nowe ciało funkcji (z odpowiednim wcięciem)
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        file_text = file.read()
    
    # Wzorzec do znalezienia definicji funkcji wraz z jej ciałem
    pattern = r'(def\s+' + re.escape(function_name) + r'\s*\([^)]*\)(?:\s*->\s*[^:]+)?\s*:)([^\n]*(?:\n[ \t]+[^\n]*)*)(?=\n\S|\Z)'
    
    # Szukaj funkcji w tekście
    match = re.search(pattern, file_text)
    if not match:
        print(f"Funkcja {function_name} nie znaleziona.")
        return False
    
    # Pobierz definicję funkcji (def ... :) i jej oryginalne ciało
    func_def = match.group(1)
    original_body = match.group(2)
    
    # Określ wcięcie na podstawie pierwszej niepustej linii oryginalnego ciała
    indentation = ""
    for line in original_body.splitlines():
        if line.strip():
            indentation = re.match(r'^[ \t]*', line).group(0)
            break
    if not indentation:
        indentation = "    "  # domyślne wcięcie Pythona
    
    # Dostosuj wcięcie dla nowego ciała
    indented_body = []
    for line in new_body.strip().splitlines():
        if line.strip():  # dla niepustych linii dodaj wcięcie
            indented_body.append(indentation + line)
        else:  # dla pustych linii po prostu dodaj je
            indented_body.append("")
    
    new_function = func_def + "\n" + "\n".join(indented_body)
    
    # Zastąp funkcję w pliku
    modified_text = re.sub(pattern, new_function, file_text, count=1)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_text)
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Użycie: python function_editor.py plik.py nazwa_funkcji \"nowe_ciało\"")
        sys.exit(1)
    
    file_path = sys.argv[1]
    function_name = sys.argv[2]
    new_body = sys.argv[3]
    
    if modify_function(file_path, function_name, new_body):
        print(f"Funkcja {function_name} została pomyślnie zmodyfikowana.")
    else:
        print(f"Nie udało się zmodyfikować funkcji {function_name}.")
