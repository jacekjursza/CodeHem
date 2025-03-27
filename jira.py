import argparse
import sys
from atlassian import Jira
from datetime import datetime

def fetch_jira_issues(url, email, token, project_key, date_from=None, date_to=None):
    """
    Pobiera zgłoszenia (issues) z Jira Cloud na podstawie podanych kryteriów.

    Args:
        url (str): URL instancji Jira Cloud (np. https://twoja-domena.atlassian.net).
        email (str): Adres email użytkownika powiązany z tokenem API.
        token (str): Token API Jira Cloud.
        project_key (str): Klucz projektu Jira (dawniej nazywany "namespace").
        date_from (str, optional): Data początkowa filtrowania (YYYY-MM-DD). Defaults to None.
        date_to (str, optional): Data końcowa filtrowania (YYYY-MM-DD). Defaults to None.

    Returns:
        list: Lista znalezionych zgłoszeń (słowniki) lub pusta lista w przypadku błędu/braku wyników.
    """
    print("--- Łączenie z Jira Cloud...")
    try:
        # Inicjalizacja klienta Jira
        # 'password' przyjmuje token API
        jira = Jira(
            url=url,
            username=email,
            password=token,
            cloud=True  # Ważne dla instancji Jira Cloud
        )
        # Proste sprawdzenie połączenia/autentykacji (opcjonalne)
        # jira.myself() # Rzuci wyjątek przy błędnej autentykacji
        print("--- Połączono pomyślnie.")

    except Exception as e:
        print(f"BŁĄD: Nie można połączyć się z Jira lub błąd autentykacji: {e}", file=sys.stderr)
        print("--- Sprawdź URL, email oraz token API.", file=sys.stderr)
        sys.exit(1) # Zakończ skrypt w przypadku błędu połączenia

    # Budowanie zapytania JQL (Jira Query Language)
    jql_parts = [f"project = '{project_key}'"]

    # Dodawanie filtrów daty (jeśli podano)
    # Zakładamy filtrowanie po dacie utworzenia ('created')
    if date_from:
        try:
            # Sprawdzenie poprawności formatu daty
            datetime.strptime(date_from, '%Y-%m-%d')
            jql_parts.append(f"created >= '{date_from}'")
        except ValueError:
            print(f"BŁĄD: Nieprawidłowy format daty 'date_from'. Użyj formatu RRRR-MM-DD.", file=sys.stderr)
            sys.exit(1)

    if date_to:
        try:
            # Sprawdzenie poprawności formatu daty
            datetime.strptime(date_to, '%Y-%m-%d')
            jql_parts.append(f"created <= '{date_to}'")
        except ValueError:
            print(f"BŁĄD: Nieprawidłowy format daty 'date_to'. Użyj formatu RRRR-MM-DD.", file=sys.stderr)
            sys.exit(1)

    # Łączenie części zapytania JQL
    jql_query = " AND ".join(jql_parts)
    jql_query += " ORDER BY created DESC" # Opcjonalnie: sortuj od najnowszych

    print(f"--- Wykonywanie zapytania JQL: {jql_query}")

    try:
        # Wykonanie zapytania JQL
        # Biblioteka domyślnie obsługuje paginację (pobieranie wyników partiami)
        # fields - określa, które pola zgłoszenia mają zostać pobrane (optymalizacja)
        results = jira.jql(jql_query, fields='key,summary,issuetype,status,created,updated')

        if not results or 'issues' not in results:
            print("--- Nie znaleziono żadnych zgłoszeń pasujących do kryteriów lub wystąpił błąd API.")
            return []

        issues = results.get('issues', [])
        total_found = results.get('total', len(issues)) # Całkowita liczba znalezionych przez JQL
        print(f"--- Znaleziono {total_found} zgłoszeń (pobrano {len(issues)}).") # Informacja o paginacji
        return issues

    except Exception as e:
        # Obsługa błędów związanych z wykonaniem zapytania JQL (np. składnia, uprawnienia)
        print(f"BŁĄD: Wystąpił problem podczas pobierania zgłoszeń z Jira: {e}", file=sys.stderr)
        print("--- Sprawdź poprawność zapytania JQL i swoje uprawnienia.", file=sys.stderr)
        return [] # Zwróć pustą listę w przypadku błędu


def main():
    # Konfiguracja parsera argumentów linii poleceń
    parser = argparse.ArgumentParser(description="Prosta aplikacja do pobierania zgłoszeń (ticketów) z Jira Cloud.")

    # Argumenty wymagane
    parser.add_argument("--url", required=True, help="URL Twojej instancji Jira Cloud (np. https://twoja-firma.atlassian.net)")
    parser.add_argument("--email", required=True, help="Adres email powiązany z kontem Jira")
    parser.add_argument("--token", required=True, help="Token API Jira Cloud (używany jako hasło)")
    parser.add_argument("--project", required=True, help="Klucz projektu Jira (np. 'PROJ', 'KANBAN') - dawny 'namespace'")

    # Argumenty opcjonalne (dla dat)
    parser.add_argument("--date-from", help="Opcjonalna data początkowa filtrowania (format RRRR-MM-DD). Pobiera zgłoszenia utworzone od tego dnia włącznie.", default=None)
    parser.add_argument("--date-to", help="Opcjonalna data końcowa filtrowania (format RRRR-MM-DD). Pobiera zgłoszenia utworzone do tego dnia włącznie.", default=None)

    # Parsowanie argumentów podanych przez użytkownika
    args = parser.parse_args()

    # Wywołanie funkcji pobierającej zgłoszenia
    fetched_issues = fetch_jira_issues(
        url=args.url,
        email=args.email,
        token=args.token,
        project_key=args.project,
        date_from=args.date_from,
        date_to=args.date_to
    )

    # Wyświetlanie wyników
    if fetched_issues:
        print("\n--- Pobrane zgłoszenia:")
        for issue in fetched_issues:
            # Dostęp do pól zgłoszenia (zgodnie z 'fields' w zapytaniu JQL)
            key = issue.get('key', 'BRAK KLUCZA')
            fields = issue.get('fields', {})
            summary = fields.get('summary', 'Brak podsumowania')
            issue_type = fields.get('issuetype', {}).get('name', 'Nieznany typ')
            status = fields.get('status', {}).get('name', 'Nieznany status')
            created_raw = fields.get('created', 'Brak daty utworzenia')

            # Formatowanie daty utworzenia
            created_formatted = created_raw
            if created_raw and created_raw != 'Brak daty utworzenia':
                try:
                    # Przykład formatowania daty (usuwa informacje o strefie czasowej dla czytelności)
                    created_dt = datetime.strptime(created_raw, '%Y-%m-%dT%H:%M:%S.%f%z')
                    created_formatted = created_dt.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    pass # Zostaw oryginalny format, jeśli parsowanie się nie uda

            print(f"- Klucz: {key}")
            print(f"  Podsumowanie: {summary}")
            print(f"  Typ: {issue_type}")
            print(f"  Status: {status}")
            print(f"  Utworzono: {created_formatted}")
            print("-" * 10) # Separator
    else:
        print("\n--- Nie pobrano żadnych zgłoszeń lub wystąpił błąd.")

# Uruchomienie głównej funkcji, jeśli skrypt jest wykonywany bezpośrednio
if __name__ == "__main__":
    main()