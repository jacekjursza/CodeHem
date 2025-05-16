"""
Command-line interface for CodeHem.
"""
import argparse
import sys
import os
import json

from codehem import CodeHem
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
import rich

def main():
    console = Console()
    parser = argparse.ArgumentParser(description='CodeHem command-line interface')
    parser.add_argument('file', help='File to analyze')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--extract', action='store_true', help='Extract code elements to JSON')
    parser.add_argument('--output', help='Output file for extracted elements')
    parser.add_argument('--raw-json', action='store_true', help='Output raw JSON without rich formatting')
    args = parser.parse_args()
    if not os.path.exists(args.file):
        console.print(f'[bold red]Error:[/bold red] File not found: {args.file}')
        sys.exit(1)
    try:
        if args.extract:
            with Progress() as progress:
                task = progress.add_task('[green]Extracting code elements...', total=3)
                content = CodeHem.load_file(args.file)
                progress.update(task, advance=1, description='[green]Creating CodeHem instance...')
                hem = CodeHem.from_raw_code(content)
                progress.update(task, advance=1, description='[green]Extracting elements...')
                elements = hem.extract(content)
                progress.update(task, advance=1, description='[green]Processing complete!')
                elements_dict = {'elements': [element.dict(exclude={'range.node'}) for element in elements.elements]}
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(elements_dict, f, indent=2)
                    console.print(Panel(f'[bold green]Success![/bold green] Extracted elements saved to [blue]{args.output}[/blue]', expand=False))
                elif args.raw_json:
                    print(json.dumps(elements_dict, indent=2))
                else:
                    console.print_json(data=elements_dict)
        else:
            instance = CodeHem.from_file_path(args.file)
            code = instance.load_file(args.file)
            result = instance.extract(code)
            rich.print(result)
    except Exception as e:
        console.print(f'[bold red]Error:[/bold red] {str(e)}')
        if args.verbose:
            import traceback
            console.print(f'[dim red]{traceback.format_exc()}[/dim red]')
        sys.exit(1)

if __name__ == '__main__':
    main()