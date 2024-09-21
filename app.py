import streamlit as st
import pandas as pd
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from collections import defaultdict, OrderedDict

@st.cache_data
def fetch_data():
    url = "https://apiresidenciaadministrativa.jfal.jus.br/api/v1/execution"
    response = requests.get(url)
    return response.json()

# Função para coletar todos os estados
def get_states(data):
    states = set(item.get("state") for item in data if item.get("state"))
    return sorted(list(states))

# Função para processar os dados
def process_data(data, application_cutoff_date=None, selected_state=None):
    date_counts = defaultdict(int)
    cutoff_date = datetime.date(2024, 8, 26)
    for item in data:
        timestamp_str = item.get("timeStamp")
        state = item.get("state")  # Supondo que o campo de estado é "state"
        if timestamp_str and (selected_state == "Geral" or selected_state == state):
            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).date()
            if application_cutoff_date == "Depois":
                if timestamp >= cutoff_date:
                    date_counts[timestamp] += 1
            elif application_cutoff_date == "Antes":
                if timestamp < cutoff_date:
                    date_counts[timestamp] += 1
            else:
                date_counts[timestamp] += 1
    return date_counts

# Função para dividir os dados em semanas
def split_by_weeks(date_counts):
    sorted_dates = sorted(date_counts.keys())
    weeks = defaultdict(list)
    if len(sorted_dates) > 0:
        initial_date = sorted_dates[0]
        date = sorted_dates[-1]
        week_num= (date - initial_date).days // 7 + 1 
        i = 0

        while date >= initial_date:
            if i == 7:
                week_num -= 1
                i = 0
            weeks[f"Semana {week_num}"].append((date, date_counts[date]))
            date = date + datetime.timedelta(days=-1)
            i+= 1

    #print(weeks)
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

def split_by_total(date_counts):
    sorted_dates = sorted(date_counts.keys())
    total = defaultdict(list)
    
    for i, date in enumerate(sorted_dates):
        total_num = i // len(date_counts) + 1
        total[total_num].append((date, date_counts[date]))
    return total[1]

def sorted_dict(data):
    sorted_keys = sorted(data.keys(), key=lambda x: int(x.split()[1]), reverse=True)
    ordered_data = OrderedDict((key, data[key]) for key in sorted_keys)
    return ordered_data

# Função para criar o gráfico
def bar(data, title="Gráfico de Barras", list_legends=None):
    sns.set_theme(style="whitegrid", context="talk", palette="deep", rc={"axes.facecolor": "#1a1a1a", "grid.color": "gray"})

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#1a1a1a')  # Fundo da figura
    ax.set_facecolor('#1a1a1a')  # Fundo do gráfico

    # Transformar os dados em um DataFrame
    weeks = []
    counts = []
    disponibility = []
    cutoff_date = datetime.date(2024, 8, 26)
    for week, values in data.items():
        total_count = 0
        disp = "Protegido por token"
        for date, count in values:
            total_count += count
            if date >= cutoff_date :
                disp = "Aberto ao público"
        weeks.append(week)
        counts.append(total_count)
        disponibility.append(disp)

    weeks.reverse()
    counts.reverse()
    disponibility.reverse()
    data = pd.DataFrame({'Interval': weeks, 'Count': counts, 'Disponiility': disponibility})
    
    barplot = sns.barplot(x='Interval', y='Count', hue='Disponiility', data=data, palette='Paired', width=0.4, legend=True)

    for i in range(len(data)):
        count_value = data['Count'][i]
        barplot.text(i, count_value + (0.05 * max(data['Count'])), str(count_value), ha='center', va='bottom', fontweight='bold', color='white')

    #plt.title(title, color='white', fontsize=16)
    plt.xticks(rotation=45, ha='right', color='white', fontsize=10)
    plt.yticks(color='white', fontsize=10)
    plt.grid(True, which='both', color='gray', linestyle='--', linewidth=0.6)
    plt.xlabel('')
    plt.ylabel('')

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")

    handles, labels = barplot.get_legend_handles_labels()  # Obtendo handles e labels
    ax.legend(handles, labels, title='', fontsize=12, loc='upper left', frameon=True, facecolor='#bbb', edgecolor='gray')


    if list_legends:
        legend = ax.legend(list_legends, fontsize=12)
        legend.get_frame().set_facecolor('#bbb')
        legend.get_frame().set_edgecolor('gray')

    plt.tight_layout()
    st.pyplot(fig)

# Função para criar o gráfico
def lineplot(data, days_filters):
    sns.set_theme(style="whitegrid", context="talk", palette="deep", rc={"axes.facecolor": "#1a1a1a", "grid.color": "gray"})

    sorted_dates = [item[0] for item in data]
    cumulative_counts = []
    cumulative_sum = 0

    interval_xaxis = 1 if days_filters==7 else 4
    date_formatter = "%A" if days_filters==7 else '%d/%m'
    title = f'{sorted_dates[-1].strftime("%d/%m/%Y")} - {sorted_dates[0].strftime("%d/%m/%Y")}' if days_filters==7 else f'{sorted_dates[0].strftime("%d/%m/%Y")} - {sorted_dates[-1].strftime("%d/%m/%Y")}'

    for date, count in data:
        cumulative_sum = count
        cumulative_counts.append(cumulative_sum)

    # Configurar o fundo da figura toda
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#1a1a1a')  # Fundo da figura
    ax.set_facecolor('#1a1a1a')  # Fundo do gráfico

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

    plt.xticks(rotation=45, ha='right', color='white', fontsize=10)
    plt.yticks(color='white', fontsize=10)
    plt.grid(True, which='both', color='gray', linestyle='--', linewidth=0.6)
    plt.title(title, fontsize=12, color="#bbb")
    
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

# Função para contar as execuções por estado
def count_executions_by_state(data):
    state_counts = defaultdict(int)
    for item in data:
        state = item.get("state")
        if state and state != "Não informado":
            state_counts[state] += 1
    return state_counts

# Função para exibir o gráfico de barras de execuções por estado
def bar_by_state(state_counts):
    sns.set_theme(style="whitegrid", context="talk", palette="deep", rc={"axes.facecolor": "#1a1a1a", "grid.color": "gray"})

    # Preparar os dados para o gráfico
    states = list(state_counts.keys())
    counts = list(state_counts.values())

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('#1a1a1a')  # Fundo da figura
    ax.set_facecolor('#1a1a1a')  # Fundo do gráfico

    barplot = sns.barplot(x=states, y=counts, palette='Paired', ax=ax)

    # Adicionar os valores em cima de cada barra
    for i, count in enumerate(counts):
        barplot.text(i, count + (0.05 * max(counts)), str(count), ha='center', va='bottom', fontweight='bold', color='white')

    # Personalizar o gráfico
    plt.xticks(rotation=45, ha='right', color='white', fontsize=10)
    plt.yticks(color='white', fontsize=10)
    plt.grid(True, which='both', color='gray', linestyle='--', linewidth=0.6)
    plt.xlabel('Estados', color='white', fontsize=12)
    plt.ylabel('Execuções', color='white', fontsize=12)

    # Remover bordas superiores e direitas
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")

    plt.tight_layout()
    st.pyplot(fig)

def metricHours(cumulative_sum):
    hours = cumulative_sum * 2.5
    if hours == int(hours):
        return f"{hours:_.0f}".replace("_", ".")
    hours_format = f"{hours:_.2f}"       # Agora formata como string
    hours_format = hours_format.replace(".", ",").replace("_", ".")
    return hours_format

def metricMoney(cumulative_sum):
    money = round(cumulative_sum * 2.5 * 99.91, 2)  # Calcula o valor primeiro
    if money == int(money):
        return f"{money:_.0f}".replace("_", ".")
    money_format = f"{money:_.2f}"       # Agora formata como string
    money_format = money_format.replace(".", ",").replace("_", ".")
    return money_format

def info_cards(data, title= ''):
    st.subheader(title)
    col1, col2, col3 = st.columns(3)

    cumulative_sum = sum(count for date, count in data)

    with col1:
        hours = metricHours(cumulative_sum)
        text = f':red[{hours} horas poupadas]' if 'Panorama' in title else f'{hours} horas poupadas'
        st.info(text, icon=":material/clock_loader_40:")
        
    with col2:
        money = metricMoney(cumulative_sum)
        text = f':red[R$ {money} economizados]' if 'Panorama' in title else f'R$ {money} economizados'
        st.info(text, icon=":material/payments:" )

    with col3:
        text = f':red[{cumulative_sum} cálculos realizados]' if 'Panorama' in title else f'{cumulative_sum} cálculos realizados'
        st.info(text, icon=":material/left_click:")

# Streamlit App
st.markdown(
    """
    <h1> Calculadora de Aposentadoria: Execuções </h1>
    <style>
    .main .block-container{
        max-width: 80%; /* Defina a largura desejada */
        padding-top: 3rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Opções de filtro
st.sidebar.header("Filtros")

filter_option_init = st.sidebar.selectbox(
    "Dados visualizados",
    ("Dados totais", "Dados sem token", "Dados com token")
)

# Obter os dados da API
data = fetch_data()

# Coletar a lista de estados e adicionar ao filtro
states = get_states(data)
states.insert(0, "Geral")  # Adicionar a opção "Geral" para incluir todos os estados
selected_state = st.sidebar.selectbox(
    "Selecione o estado",
    states
)

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


data_map = {
    "Dados totais": process_data(data, selected_state=selected_state),
    "Dados sem token": process_data(data, application_cutoff_date="Depois", selected_state=selected_state),
    "Dados com token": process_data(data, application_cutoff_date="Antes", selected_state=selected_state)
}

# Processar os dados
date_counts = data_map[filter_option_init]
option_type = ''
selected_options = []
selected_data = []
# Aplicar a lógica de filtragem com base na escolha
if filter_option == "Últimos 7 dias":
    weeks = sorted_dict(split_by_weeks(date_counts))
    option_type = st.sidebar.selectbox(
        "Selecione a semana",
        list(weeks.keys())
    )
    if len(weeks) > 0:
        selected_data = weeks[option_type]
    selected_options = weeks

elif filter_option == "Últimos 30 dias":
    months = sorted_dict(split_by_months(date_counts))
    option_type = st.sidebar.selectbox(
        "Selecione o mês",
        list(months.keys())
    )
    if len(months) > 0:
        selected_data = months[option_type]
    selected_options = months

elif filter_option == "Últimos 90 dias":
    quarters = sorted_dict(split_by_quarters(date_counts))
    option_type = st.sidebar.selectbox(
        "Selecione o trimestre",
        list(quarters.keys())
    )
    if len(quarters) > 0:
        selected_data = quarters[option_type]
    selected_options = quarters


info_cards(selected_data, title=option_type)

# Plotar os dados filtrados
if selected_data:
    lineplot(selected_data, days)
else:
    st.write("Nenhum dado disponível para o intervalo selecionado.")


info_cards(split_by_total(date_counts), title=f"Panorama {selected_state}")

# Plotar os dados filtrados
if selected_options:
    bar(selected_options, days)
else:
    st.write("Nenhum dado disponível para o intervalo selecionado.")

'''
# Contar execuções por estado
state_counts = count_executions_by_state(selected_data) #, selected_state)

# Exibir o gráfico de barras com execuções por estado
st.subheader("Execuções por Estado")
bar_by_state(state_counts)
'''
