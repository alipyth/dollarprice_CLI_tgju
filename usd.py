# currency_cli.py
import requests
import json
import sys
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box
from datetime import datetime

console = Console()

# Currency settings
currencies = {
    'usd': {
        'name': 'US Dollar',
        'symbol': '$',
        'alanchand': 'https://alanchand.com/currencies-price/usd',
        'tgju_profile': 'price_dollar_rl'
    },
    'eur': {
        'name': 'Euro',
        'symbol': '€',
        'alanchand': 'https://alanchand.com/currencies-price/eur',
        'tgju_profile': 'price_eur'
    },
    'aed': {
        'name': 'UAE Dirham',
        'symbol': 'AED',
        'alanchand': 'https://alanchand.com/currencies-price/aed',
        'tgju_profile': 'price_aed'
    },
    'try': {
        'name': 'Turkish Lira',
        'symbol': '₺',
        'alanchand': 'https://alanchand.com/currencies-price/try',
        'tgju_profile': 'price_try'
    },
    'gbp': {
        'name': 'British Pound',
        'symbol': '£',
        'alanchand': 'https://alanchand.com/currencies-price/gbp',
        'tgju_profile': 'price_gbp'
    },
    'cny': {
        'name': 'Chinese Yuan',
        'symbol': '¥',
        'alanchand': 'https://alanchand.com/currencies-price/cny',
        'tgju_profile': 'price_cny'
    },
    'iqd': {
        'name': 'Iraqi Dinar',
        'symbol': 'IQD',
        'alanchand': 'https://alanchand.com/currencies-price/iqd',
        'tgju_profile': 'price_iqd'
    },
    'aud': {
        'name': 'Australian Dollar',
        'symbol': 'A$',
        'alanchand': 'https://alanchand.com/currencies-price/aud',
        'tgju_profile': 'price_aud'
    }
}

SESSION = requests.Session()
SESSION.trust_env = False


def format_price(price_str):
    """Format price with commas for better readability"""
    try:
        clean = ''.join(filter(str.isdigit, str(price_str)))
        if clean:
            formatted = '{:,}'.format(int(clean))
            return formatted
    except:
        pass
    return str(price_str)


def fetch_from_tgju(currency_code, timeout=15):
    """Fetch price from tgju.org (primary source)"""
    profile = currencies[currency_code]['tgju_profile']
    
    api_url = f"https://api.tgju.org/v1/market/indicator/today-table-data/{profile}"
    
    params = {
        'lang': 'fa',
        'draw': 1,
        'start': 0,
        'length': 1,
        'search': ''
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.tgju.org/',
        'Origin': 'https://www.tgju.org'
    }
    
    try:
        resp = SESSION.get(api_url, headers=headers, params=params, timeout=timeout,
                          proxies={"http": None, "https": None})
        resp.raise_for_status()
        
        data = resp.json()
        
        if data.get('data') and len(data['data']) > 0:
            record = data['data'][0]
            price_raw = record[0]
            time_raw = record[1]
            
            price_formatted = format_price(price_raw)
            
            return price_formatted, time_raw, "tgju.org"
        
        return None, None, None
    except Exception:
        return None, None, None


def fetch_from_alanchand(currency_code, timeout=15):
    """Fetch price from alanchand.com (fallback)"""
    url = currencies[currency_code]['alanchand']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resp = SESSION.get(url, headers=headers, timeout=timeout,
                          proxies={"http": None, "https": None})
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        price_div = soup.select_one(
            'body > main > section.container.mostPopularRate > div > div > div:nth-child(1) > div > div > div > div'
        )
        
        if price_div:
            price_text = price_div.get_text(strip=True)
            if "%" in price_text:
                price_text = price_text.split("%")[0].strip()
            
            price_formatted = format_price(price_text)
            return price_formatted, None, "alanchand.com"
        
        return None, None, None
    except Exception:
        return None, None, None


def fetch_price_with_fallback(currency_code):
    """Try to fetch price: first tgju, then alanchand"""
    currency_name = currencies[currency_code]['name']
    console.print(f"[yellow]>> Fetching {currency_name}...[/yellow]")
    
    # Priority 1: tgju
    price, time_raw, source = fetch_from_tgju(currency_code)
    if price:
        if time_raw:
            console.print(f"[green]✓ Got from {source} (Time: {time_raw})[/green]")
            return price, f"{source} @ {time_raw}"
        else:
            console.print(f"[green]✓ Got from {source}[/green]")
            return price, source
    
    # Fallback: alanchand
    console.print(f"[yellow]⚠ Primary source failed, trying fallback...[/yellow]")
    price, _, source = fetch_from_alanchand(currency_code)
    if price:
        console.print(f"[green]✓ Got from {source}[/green]")
        return price, source
    
    return None, None


def show_price(currency_code):
    """Display price for a single currency"""
    price, source = fetch_price_with_fallback(currency_code)
    currency = currencies[currency_code]
    
    if price:
        content = (
            f"[bold cyan]💱 {currency['name']} ({currency['symbol']})[/bold cyan]\n\n"
            f"[bold yellow]┌─ PRICE:[/bold yellow]\n"
            f"[bold yellow]│   [/bold yellow][bold white]{price}[/bold white] IRR\n"
            f"[bold yellow]└─[/bold yellow]\n\n"
            f"[dim]📡 Source: {source}[/dim]"
        )
        
        panel = Panel(
            content,
            title="💰 Live Rate",
            border_style="green",
            padding=(1, 2)
        )
        console.print(panel)
    else:
        console.print(f"[red]✗ Error: {currency['name']} price not available[/red]")


def show_all_prices():
    """Display all currencies in a table"""
    table = Table(
        title="💰 Live Currency Rates",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_header=True
    )
    table.add_column("Code", style="bold cyan", justify="center", width=6)
    table.add_column("Currency", style="white", width=18)
    table.add_column("Price (IRR)", style="bold green", justify="right", width=20)
    table.add_column("Source", style="yellow", width=28)
    
    for code, info in currencies.items():
        # First try tgju
        price, time_raw, source = fetch_from_tgju(code)
        
        # If failed, try alanchand
        if not price:
            price, _, source = fetch_from_alanchand(code)
            if not price:
                price = "N/A"
                source = "Failed"
        else:
            if time_raw:
                source = f"tgju ({time_raw})"
            else:
                source = "tgju"
        
        table.add_row(
            code.upper(),
            info['name'],
            price if price else "---",
            str(source)
        )
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def header():
    """Display program header"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    console.print("\n")
    console.print("[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║       💱  CURRENCY PRICE CLI             ║[/bold cyan]")
    console.print(f"[bold cyan]║       {now}                  ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]")
    console.print("\n")


def show_help():
    """Display help menu"""
    console.print("\n[bold yellow]📖 HELP:[/bold yellow]")
    console.print("  [cyan]all[/cyan] or [cyan]a[/cyan]     → Show all currencies")
    console.print("  [cyan]usd[/cyan] / [cyan]eur[/cyan] / ... → Show specific currency")
    console.print("  [cyan]help[/cyan] / [cyan]h[/cyan]   → Show this help")
    console.print("  [cyan]exit[/cyan] / [cyan]q[/cyan]    → Exit program")
    console.print("\n[dim]Supported currencies: usd, eur, aed, try, gbp, cny, iqd, aud[/dim]\n")


def main():
    """Main program function"""
    console.clear()
    header()
    
    # Auto-show USD on start
    show_price('usd')
    
    console.print("\n[dim]💡 Commands: all=all currencies | help=help | exit=quit[/dim]\n")
    
    while True:
        try:
            cmd = Prompt.ask("[bold cyan]⌨️  Command[/bold cyan]").lower().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold green]👋 Goodbye![/bold green]")
            break
        
        if cmd in ['exit', 'q', 'quit']:
            console.print("\n[bold green]👋 Goodbye![/bold green]")
            break
        
        if cmd in ['help', 'h', '?']:
            show_help()
            continue
        
        if cmd in ['all', 'a']:
            show_all_prices()
            continue
        
        if cmd in currencies:
            show_price(cmd)
            continue
        
        console.print(f"[red]✗ Invalid command or currency: '{cmd}'[/red]")


if __name__ == "__main__":
    main()
