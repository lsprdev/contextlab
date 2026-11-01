"""Menu interativo; o cálculo e a consulta ficam em módulos próprios."""

import argparse
from decimal import Decimal, InvalidOperation

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .conversao import converter_para_brl
from .cotacoes import ErroCotacao, buscar_cotacao, cotacao_demonstracao


def ler_valor(texto: str) -> Decimal:
    """Aceita vírgula ou ponto decimal, sem separadores de milhares."""
    texto = texto.strip()
    if len(texto) > 40 or ("," in texto and "." in texto):
        raise ValueError("Digite um número sem separadores de milhares.")
    try:
        valor = Decimal(texto.replace(",", "."))
    except InvalidOperation as erro:
        raise ValueError("Digite um número, como 10 ou 10,50.") from erro
    if not valor.is_finite() or valor < 0 or valor > Decimal("1e12"):
        raise ValueError("Digite um valor entre zero e 1 trilhão.")
    return valor


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Dólar e euro em reais, com taxas diárias.")
    parser.add_argument("--demo", action="store_true", help="Usar valores fictícios, sem internet")
    args = parser.parse_args(argv)
    console = Console()
    buscar = cotacao_demonstracao if args.demo else buscar_cotacao
    console.print(Panel("Dólar e euro em reais", title="Câmbio", border_style="cyan"))
    if args.demo:
        console.print("DEMONSTRAÇÃO: as cotações são fictícias.", style="yellow")
    else:
        console.print("Fonte: Frankfurter • taxas diárias; confira a data da cotação.")
    try:
        while True:
            console.print("\n1  Consultar cotações\n2  Converter um valor\n0  Sair")
            escolha = Prompt.ask("Opção", choices=["1", "2", "0"], console=console)
            if escolha == "0":
                console.print("Até a próxima!", style="cyan")
                return 0
            try:
                if escolha == "1":
                    tabela = Table("Moeda", "1 unidade em BRL", "Data", "Fonte")
                    with console.status("Consultando cotações…", spinner="dots"):
                        cotacoes = [buscar(moeda) for moeda in ("USD", "EUR")]
                    for cotacao in cotacoes:
                        tabela.add_row(cotacao.moeda, f"R$ {cotacao.taxa:.4f}".replace(".", ","),
                                       cotacao.data.isoformat(), cotacao.fonte)
                    console.print(tabela)
                else:
                    moeda = Prompt.ask("Moeda", choices=["USD", "EUR"], default="USD",
                                       case_sensitive=False, console=console).upper()
                    valor = ler_valor(Prompt.ask("Quantidade (ex.: 10,50)", console=console))
                    with console.status("Consultando cotação…", spinner="dots"):
                        cotacao = buscar(moeda)
                    total = converter_para_brl(valor, cotacao.taxa)
                    console.print(Panel(f"{valor} {moeda} = R$ {total:.2f}".replace(".", ","),
                                        title="Conversão", border_style="green"))
                    console.print(f"Taxa: {cotacao.taxa} BRL por {moeda} • {cotacao.data} • {cotacao.fonte}")
            except (ValueError, ErroCotacao) as erro:
                console.print(str(erro), style="red", markup=False)
    except (EOFError, KeyboardInterrupt):
        console.print("\nEncerrado.")
        return 0
