import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.express as px
import json
from babel.dates import format_datetime
from unidecode import unidecode

def loading_html(file="app.html"):
    # Carrega o conteúdo HTML do arquivo
    with open(file, 'r') as f:
        html_string = f.read()

    return html_string

@st.cache_data(ttl=60*5) # 5 minutos
def fetch_data():
    url = "https://apiresidenciaadministrativa.jfal.jus.br/api/v1/execution"
    response = requests.get(url)
    return response.json()

def loading_data():
    data = fetch_data()
    df = pd.DataFrame(data)
    df['timeStamp'] = pd.to_datetime(df['timeStamp']).dt.tz_convert('America/Sao_Paulo')
    df['duration'] = df['duration'].astype(float) 
    df = df.rename(columns={
        'duration': 'Execuções realizadas'
    })
    return df

def process_data_type_visualization(df, type_data_visualization):
    cutoff_date = pd.Timestamp(2024, 8, 26).date()

    if type_data_visualization != "Dados totais":
        df = df[df['timeStamp'].dt.date >= cutoff_date if type_data_visualization == "Aberto ao público" else df['timeStamp'].dt.date < cutoff_date] 
    
    return df

def process_data_state(df, selected_state):
    df = df[df['state'] == selected_state] if selected_state != 'Geral' else df
    return df

def split_by_interval(df, interval, type_interval):
    date_counts = df['timeStamp'].dt.date.value_counts()
    sorted_dates = sorted(date_counts.keys(), reverse=True)

    interval_dates = defaultdict(list)
    if len(sorted_dates) > 0:
        initial_date = sorted_dates[-1]
        date = sorted_dates[0]
        interval_num= (date - initial_date).days // interval + 1 
        i = 0

        while date >= initial_date:
            if i == interval:
                interval_num -= 1
                i = 0
            try:
                days = int(date_counts[date]) 
            except:
                days = 0 
            interval_dates[f"{type_interval} {interval_num}"].append((date, days))
            date = date + timedelta(days=-1)
            i += 1

    return interval_dates

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

def metricCounts(cumulative_sum):
    cumulative_sum_format = f"{cumulative_sum:_.0f}" 
    cumulative_sum_format = cumulative_sum_format.replace("_", ".")
    return cumulative_sum_format

def metrics_cards(cumulative_sum, title, delta=None, color='gray'):
    st.subheader(title)
    col1, col2, col3 = st.columns(3)
    with col1:
        money = metricMoney(cumulative_sum)
        st.metric(label=f":{color}[ :material/payments: Impacto econômico]", value=f"R$ {money}")

        
    with col2:
        hours = metricHours(cumulative_sum)
        st.metric(label=f":{color}[:material/clock_loader_40: Custo de oportunidade]", value=f"{hours} horas")
        
    with col3:
        count = metricCounts(cumulative_sum)
        st.metric(label=f":{color}[ :material/left_click:  Cálculos realizados]", value=count, delta=delta )

def info_cards(dfs, index_atual, title= ''):
    delta = 0
    keys = list(dfs.keys())
    df = dfs[keys[index_atual]]
    cumulative_sum = int(sum(df['Execuções realizadas']))
    if index_atual < len(dfs) - 1:
        df_anterior=dfs[keys[index_atual+1]]
        cumulative_sum_anterior = int(sum(df_anterior['Execuções realizadas']))
        delta=round((cumulative_sum / cumulative_sum_anterior - 1)*100, 2)
        delta= f"{delta:_.2f} %"
        delta = delta.replace(".", ",").replace("_", ".")

    metrics_cards(cumulative_sum, title, delta)


def map(df):
    df = df[df['state'] != "Não informado"]

    df_map=df.groupby('state').agg({'Execuções realizadas': 'sum'}).reset_index()
    df_map['Execuções realizadas'] = df_map['Execuções realizadas'].astype(int)
    with open('br_states.json', 'r', encoding='utf-8') as f:
        brasil_geo = json.load(f)
    
    fig = px.choropleth_mapbox(
        df_map,
        geojson=brasil_geo,
        locations='state',
        featureidkey='geometry_name',  # Ajustado para 'sigla'
        color='Execuções realizadas',
        color_continuous_scale="Blues",
        mapbox_style="carto-positron",
        zoom=3,
        center={"lat": -15.7801, "lon": -47.9292},
        opacity=0.7,
        labels={'state': 'Estado', 'Execuções realizadas': 'Usos'}
    )

    # Ajustar layout do mapa
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    # Mostrar o mapa no Streamlit
    st.plotly_chart(fig)

    return df_map

def bar_hour(df):

    df['hour'] = df['timeStamp'].dt.strftime('%H:00')  # Formatar como 'HH:00'
    execucoes_por_hora = df.groupby('hour').size().reset_index(name='execucoes')

    fig = px.bar(
        execucoes_por_hora,
        x='hour',
        y='execucoes',
        labels={'hour': 'Horário', 'execucoes': 'Número de Execuções'},
        color='execucoes',
        color_continuous_scale='Blues'
    )

    st.plotly_chart(fig)


if __name__ == "__main__":

    df = loading_data()

    # Streamlit App
    st.markdown( loading_html(), unsafe_allow_html=True)

    st.sidebar.header("Filtros")

    filter_type_data = st.sidebar.selectbox(
        "Dados visualizados",
        ("Aberto ao público", "Dados totais", "Com token")
    )

    df = process_data_type_visualization(df, filter_type_data)

    states = list(df[df['state'] != "Não informado"]['state'].sort_values().unique())
    states.insert(0, "Geral")
    selected_state = st.sidebar.selectbox(
        "Selecione o estado",
        states
    )

    filter_option = st.sidebar.selectbox(
        "Selecione o intervalo de tempo",
        ("Por semana", "Por mês", "Por trimestre")
    )

    # Mapear a opção selecionada para um número de dias
    days_map = {
        "Por semana": 7,
        "Por mês": 30,
        "Por trimestre": 90
    }
    days = days_map[filter_option]
    df = process_data_state(df, selected_state=selected_state)
    interval_dates = split_by_interval(df, interval=days, type_interval=filter_option[4:].capitalize())

    option_type = st.sidebar.selectbox(
        f"Selecione {filter_option[4:]}",
        list(interval_dates.keys())
    )
    store = f"{option_type}{filter_option}{selected_state}{filter_type_data}.pkl"
    store = unidecode(store.replace(" ", "").lower())

    charts = {
        interval: pd.DataFrame(
            data=[
                (d.strftime("%d/%m"), format_datetime(d, "EEEE", locale='pt_BR')[:3], c) 
                for d, c in sorted(values)],
            columns=['Data', 'Dia' , 'Execuções realizadas']
        ) for interval, values in interval_dates.items()
    }


    date_max = max(interval_dates[option_type], key=lambda x: x[0])[0]
    date_min = min(interval_dates[option_type], key=lambda x: x[0])[0]

    chart = charts[option_type] if len(charts) else {}
    title = f"{selected_state}: {option_type} [{date_min.strftime('%d/%m')} - {date_max.strftime('%d/%m')}] ({filter_type_data})  "

    info_cards(charts, index_atual=list(charts.keys()).index(option_type), title=title)


    fig = px.line(chart, x='Dia' if filter_option[4:].capitalize() == 'Semana' else 'Data', y='Execuções realizadas', markers=True, text='Execuções realizadas')
    fig.update_traces(textposition='top center', textfont_size=16)
    st.plotly_chart(fig)
    
    df_filter = df[(df['timeStamp'].dt.date >= date_min) & (df['timeStamp'].dt.date <= date_max)]
    if filter_type_data != 'Com token':
        df_map = map(df_filter)

    bar_hour(df_filter)

    metrics_cards(int(sum(df['Execuções realizadas'])), title="Panorama Geral", color="blue")

    col1, col2 = st.columns(2)
    with col1:
        charts = {key: charts[key] for key in sorted(charts)[:8]}
        bar = pd.DataFrame(data=[(key, sum(v['Execuções realizadas'])) for key, v in charts.items()], columns=['Período', 'Quantidade de execuções'])
        fig = px.bar(
                bar, 
                y='Período', 
                x='Quantidade de execuções', 
                text='Quantidade de execuções',
                orientation='h')
        fig.update_traces(textposition='outside', textfont_size=16)
        st.plotly_chart(fig)
    with col2:
        bar_hour(df)

    

    
    