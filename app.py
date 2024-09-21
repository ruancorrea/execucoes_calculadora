import streamlit as st
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from collections import defaultdict, OrderedDict

# Função para obter dados da API
def fetch_data():
    url = "https://apiresidenciaadministrativa.jfal.jus.br/api/v1/execution"
    response = requests.get(url)
    return response.json()

# Função para processar os dados
def process_data(data):
    date_counts = defaultdict(int)
    for item in data:
        timestamp_str = item.get("timeStamp")
        if timestamp_str:
            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).date()
            date_counts[timestamp] += 1
    return date_counts

# Função para dividir os dados em semanas
def split_by_weeks(date_counts):
    sorted_dates = sorted(date_counts.keys())
    initial_date = sorted_dates[0]
    date = sorted_dates[-1]
    initial_date = sorted_dates[0]
    weeks = defaultdict(list)
    i = len(sorted_dates) + 1

    while date >= initial_date:
        week_num = i // 7 + 1
        weeks[f"Semana {week_num}"].append((date, date_counts[date]))
        date = date + datetime.timedelta(days=-1)
        i-= 1

    return weeks

# Função para dividir os dados em meses (30 dias)
def split_by_months(date_counts):
    sorted_dates = sorted(date_counts.keys())
    months = defaultdict(list)
    
    for i, date in enumerate(sorted_dates):
        month_num = i // 30 + 1
        months[f"Mês {month_num}"].append((date, date_counts[date]))
    
    return months

# Função para dividir os dados em trimestres (90 dias)
def split_by_quarters(date_counts):
    sorted_dates = sorted(date_counts.keys())
    quarters = defaultdict(list)
    
    for i, date in enumerate(sorted_dates):
        quarter_num = i // 90 + 1
        quarters[f"Trimestre {quarter_num}"].append((date, date_counts[date]))
    
    return quarters

def sorted_dict(data):
    sorted_keys = sorted(data.keys(), key=lambda x: int(x.split()[1]), reverse=True)
    ordered_data = OrderedDict((key, data[key]) for key in sorted_keys)
    return ordered_data

# Função para criar o gráfico
def plot_data(data, days_filters):
    sns.set_theme(style="whitegrid", context="talk", palette="deep", rc={"axes.facecolor": "#1a1a1a", "grid.color": "gray"})

    sorted_dates = [item[0] for item in data]
    cumulative_counts = []
    cumulative_sum = 0

    interval_xaxis = 1 if days_filters==7 else 4
    date_formatter = "%A" if days_filters==7 else '%d/%m'
    xlabel = "Dia" if days_filters==7 else 'Data'

    for date, count in data:
        cumulative_sum = count
        cumulative_counts.append(cumulative_sum)

    # Configurar o fundo da figura toda
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#1a1a1a')  # Fundo da figura
    ax.set_facecolor('#1a1a1a')  # Fundo do gráfico

    #plt.plot(sorted_dates, cumulative_counts, marker='o', linestyle='-', color='blue', label='Quantidade')
    sns.lineplot(x=sorted_dates, y=cumulative_counts, marker='o', color='cyan', linewidth=2.5, ax=ax)

    y_max = max(cumulative_counts)
    offset = y_max * 0.03  # Ajuste de 3% baseado no valor máximo do eixo Y

    # Adicionando os valores em cima de cada ponto
    for i, (date, count) in enumerate(data):
        y_pos = cumulative_counts[i] + offset  # Deslocamento dinâmico acima do ponto
        ax.text(sorted_dates[i], y_pos, f'{count}', color='white', ha='center', fontsize=12)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_formatter))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval_xaxis))

    list_legends = ["Quantidade de execuções"]
    cutoff_date = datetime.date(2024, 8, 26)
    if cutoff_date in sorted_dates:
        ax.axvline(x=cutoff_date, color='cyan', linestyle='--', label='Abertura ao público')
        list_legends.append('Abertura ao público')

    #ax.set_xlabel('Data', color='white', fontsize=12)
    #ax.set_ylabel('Quantidade de execuções', color='white', fontsize=12)
    #plt.title('Calculadora de Aposentadoria', color='white', fontsize=16)
    plt.xticks(rotation=45, ha='right', color='white', fontsize=10)
    plt.yticks(color='white', fontsize=10)
    plt.grid(True, which='both', color='gray', linestyle='--', linewidth=0.6)
    
    # Remover bordas superiores e direitas
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")

    # Adicionar legenda com fundo escuro
    legend = ax.legend(list_legends, fontsize=12)
    legend.get_frame().set_facecolor('#bbbbbb')  # Cor de fundo da legenda
    legend.get_frame().set_edgecolor('gray')  # Cor da borda da legenda

    # Layout otimizado
    plt.tight_layout()

    st.pyplot(plt)

# Streamlit App
st.markdown("### Calculadora de Aposentadoria: Execuções")  # Título grande (nível 1)

# Opções de filtro
st.sidebar.header("Filtros")
filter_option = st.sidebar.selectbox(
    "Selecione o intervalo de tempo",
    ("Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias")
)

# Mapear a opção selecionada para um número de dias
days_map = {
    "Últimos 7 dias": 7,
    "Últimos 30 dias": 30,
    "Últimos 90 dias": 90
}
days = days_map[filter_option]

# Obter os dados da API
data = fetch_data()

# Processar os dados
date_counts = process_data(data)

# Aplicar a lógica de filtragem com base na escolha
if filter_option == "Últimos 7 dias":
    weeks = sorted_dict(split_by_weeks(date_counts))
    week_choice = st.sidebar.selectbox(
        "Selecione a semana",
        list(weeks.keys())
    )
    selected_data = weeks[week_choice]

elif filter_option == "Últimos 30 dias":
    months = sorted_dict(split_by_months(date_counts))
    month_choice = st.sidebar.selectbox(
        "Selecione o mês",
        list(months.keys())
    )
    selected_data = months[month_choice]

elif filter_option == "Últimos 90 dias":
    quarters = sorted_dict(split_by_quarters(date_counts))
    quarter_choice = st.sidebar.selectbox(
        "Selecione o trimestre",
        list(quarters.keys())
    )
    selected_data = quarters[quarter_choice]

# Plotar os dados filtrados
if selected_data:
    plot_data(selected_data, days)
else:
    st.write("Nenhum dado disponível para o intervalo selecionado.")
