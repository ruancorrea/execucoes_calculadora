import streamlit as st
import pandas as pd
import requests
import datetime
from datetime import timedelta
import json
from unidecode import unidecode
from typing import Optional, Dict, Any, List
import plotly.express as px

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Painel de Cálculos Previdenciários | JFAL",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CSS DINÂMICO ADAPTÁVEL A MODO LIGHT E DARK
# ==============================================================================
DYNAMIC_THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    .main .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 96%;
    }

    /* Cabeçalho Institucional Gradiente (Harmonioso em Light e Dark) */
    .jfal-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #0284c7 100%);
        border-radius: 14px;
        padding: 1.3rem 1.8rem;
        color: #ffffff !important;
        margin-bottom: 1.4rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .jfal-header-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0;
        color: #ffffff !important;
        letter-spacing: -0.01em;
    }

    .jfal-header-sub {
        font-size: 0.9rem;
        color: #e0f2fe !important;
        margin: 0.25rem 0 0 0;
    }

    .jfal-badge {
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.35);
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: #ffffff !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Cards de Métricas: 100% integrados às variáveis de tema do Streamlit */
    .metric-card-box {
        background-color: var(--secondary-background-color, rgba(128, 128, 128, 0.08));
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 12px;
        padding: 1.05rem 1.2rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .metric-card-box:hover {
        border-color: rgba(56, 189, 248, 0.6);
        transform: translateY(-2px);
    }

    .metric-title {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-color, #64748b);
        opacity: 0.85;
        letter-spacing: 0.04em;
        margin-bottom: 0.3rem;
    }

    .metric-val {
        font-family: 'Outfit', sans-serif;
        font-size: 1.75rem;
        font-weight: 700;
        color: #0284c7;
        line-height: 1.15;
    }

    @media (prefers-color-scheme: dark) {
        .metric-val {
            color: #38bdf8;
        }
    }

    .metric-sub {
        font-size: 0.78rem;
        color: var(--text-color, #64748b);
        opacity: 0.75;
        margin-top: 0.3rem;
    }

    .section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-color, inherit);
        margin: 1.6rem 0 0.3rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .section-desc {
        font-size: 0.88rem;
        color: var(--text-color, #64748b);
        opacity: 0.75;
        margin-bottom: 1rem;
        line-height: 1.4;
    }

    .divider-line {
        border-top: 1px solid rgba(148, 163, 184, 0.2);
        margin: 2rem 0 1.5rem 0;
    }
</style>
"""
st.markdown(DYNAMIC_THEME_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. CONSTANTES ECONÔMICAS INSTITUCIONAIS DA JFAL
# ==============================================================================
HORAS_POR_CALCULO = 2.5     # Custo de oportunidade: 2.5h economizadas por cálculo
VALOR_HORA_TECNICA = 99.91  # Custo da hora técnica/pericial estabelecido no modelo da JFAL
CUTOFF_DATE = datetime.date(2024, 8, 26)  # Marco histórico de abertura pública

# ==============================================================================
# 4. FUNÇÃO DE DETECÇÃO AUTOMÁTICA DO TEMA ATUAL (LIGHT OU DARK)
# ==============================================================================
def get_current_theme() -> str:
    """Detecta automaticamente se o tema do Streamlit está configurado como dark ou light."""
    try:
        if hasattr(st, "context") and hasattr(st.context, "theme"):
            theme_dict = dict(st.context.theme)
            base = theme_dict.get("base") or theme_dict.get("type")
            if base in ["dark", "light"]:
                return base
    except Exception:
        pass

    try:
        opt_theme = st.get_option("theme.base")
        if opt_theme in ["dark", "light"]:
            return opt_theme
    except Exception:
        pass

    return "dark"  # Padrão dark se não identificado

# ==============================================================================
# 5. RENDERIZADOR ROBUSTO ECHARTS (ADAPTAÇÃO AUTOMÁTICA AO TEMA)
# ==============================================================================
def render_echarts(
    options: Dict[str, Any],
    height: str = "400px",
    key: Optional[str] = None
) -> None:
    """Renderiza gráficos Apache ECharts com detecção e sincronização automática de tema."""
    try:
        height_px = int(height.replace("px", "").strip())
    except Exception:
        height_px = 400

    options_json = json.dumps(options, ensure_ascii=False)
    chart_id = f"ec_{unidecode((key or 'chart')).replace('-', '_').replace(' ', '_')}_{abs(hash(options_json)) % 100000}"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background-color: transparent !important;
            }}
            #{chart_id} {{
                width: 100%;
                height: {height_px}px;
            }}
        </style>
    </head>
    <body>
        <div id="{chart_id}"></div>
        <script>
            (function() {{
                var rawOption = {options_json};
                var chartDom = document.getElementById('{chart_id}');
                var myChart = null;
                var currentTheme = 'dark';

                function detectStreamlitTheme() {{
                    try {{
                        if (window.parent && window.parent.document) {{
                            var htmlTheme = window.parent.document.documentElement.getAttribute('data-theme');
                            if (htmlTheme === 'dark') return 'dark';
                            if (htmlTheme === 'light') return 'light';

                            var appEl = window.parent.document.querySelector('.stApp') || window.parent.document.body;
                            if (appEl) {{
                                var bg = window.getComputedStyle(appEl).backgroundColor;
                                var rgb = bg.match(/\\d+/g);
                                if (rgb && rgb.length >= 3) {{
                                    var luma = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
                                    return luma < 140 ? 'dark' : 'light';
                                }}
                            }}
                        }}
                    }} catch(e) {{}}

                    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {{
                        return 'dark';
                    }}
                    return 'light';
                }}

                function applyThemeColors(opt, theme) {{
                    var isDark = (theme === 'dark');

                    var textColor = isDark ? '#cbd5e1' : '#475569';
                    var titleColor = isDark ? '#f8fafc' : '#0f172a';
                    var gridLineColor = isDark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)';
                    var tooltipBg = isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.96)';
                    var tooltipBorder = isDark ? '#38bdf8' : '#0284c7';
                    var tooltipTextColor = isDark ? '#f8fafc' : '#0f172a';
                    var legendTextColor = isDark ? '#e2e8f0' : '#334155';

                    if (!opt.tooltip) opt.tooltip = {{}};
                    opt.tooltip.backgroundColor = tooltipBg;
                    opt.tooltip.borderColor = tooltipBorder;
                    if (!opt.tooltip.textStyle) opt.tooltip.textStyle = {{}};
                    opt.tooltip.textStyle.color = tooltipTextColor;

                    if (opt.title) {{
                        if (!opt.title.textStyle) opt.title.textStyle = {{}};
                        opt.title.textStyle.color = titleColor;
                    }}

                    if (opt.legend) {{
                        if (!opt.legend.textStyle) opt.legend.textStyle = {{}};
                        opt.legend.textStyle.color = legendTextColor;
                    }}

                    if (opt.xAxis) {{
                        var xAxes = Array.isArray(opt.xAxis) ? opt.xAxis : [opt.xAxis];
                        xAxes.forEach(function(axis) {{
                            if (!axis.axisLabel) axis.axisLabel = {{}};
                            axis.axisLabel.color = textColor;
                            if (axis.splitLine && axis.splitLine.lineStyle) {{
                                axis.splitLine.lineStyle.color = gridLineColor;
                            }}
                            if (axis.splitArea && axis.splitArea.areaStyle) {{
                                axis.splitArea.areaStyle.color = isDark
                                    ? ['rgba(30, 41, 59, 0.25)', 'rgba(15, 23, 42, 0.25)']
                                    : ['rgba(241, 245, 249, 0.6)', 'rgba(255, 255, 255, 0.6)'];
                            }}
                        }});
                    }}

                    if (opt.yAxis) {{
                        var yAxes = Array.isArray(opt.yAxis) ? opt.yAxis : [opt.yAxis];
                        yAxes.forEach(function(axis) {{
                            if (!axis.axisLabel) axis.axisLabel = {{}};
                            axis.axisLabel.color = textColor;
                            if (axis.nameTextStyle) axis.nameTextStyle.color = textColor;
                            if (!axis.splitLine) axis.splitLine = {{}};
                            if (!axis.splitLine.lineStyle) axis.splitLine.lineStyle = {{}};
                            axis.splitLine.lineStyle.color = gridLineColor;
                        }});
                    }}

                    if (opt.visualMap) {{
                        if (!opt.visualMap.textStyle) opt.visualMap.textStyle = {{}};
                        opt.visualMap.textStyle.color = textColor;

                        if (opt.visualMap.inRange && opt.visualMap.inRange.color) {{
                            if (isDark) {{
                                opt.visualMap.inRange.color = ["#1e293b", "#0369a1", "#0284c7", "#38bdf8", "#10b981"];
                            }} else {{
                                opt.visualMap.inRange.color = ["#ebedf0", "#bae6fd", "#38bdf8", "#0284c7", "#1e3a8a"];
                            }}
                        }}
                    }}

                    if (opt.calendar) {{
                        if (!opt.calendar.itemStyle) opt.calendar.itemStyle = {{}};
                        opt.calendar.itemStyle.color = isDark ? '#1e293b' : '#ebedf0';
                        opt.calendar.itemStyle.borderColor = isDark ? '#0f172a' : '#ffffff';
                        if (!opt.calendar.dayLabel) opt.calendar.dayLabel = {{}};
                        opt.calendar.dayLabel.color = textColor;
                        if (!opt.calendar.monthLabel) opt.calendar.monthLabel = {{}};
                        opt.calendar.monthLabel.color = textColor;
                    }}

                    if (opt.series) {{
                        opt.series.forEach(function(s) {{
                            if (s.type === 'line') {{
                                if (s.name && s.name.indexOf('Média Móvel') !== -1) {{
                                    s.itemStyle = {{ color: isDark ? '#fbbf24' : '#d97706' }};
                                }} else {{
                                    s.itemStyle = {{ color: isDark ? '#38bdf8' : '#0284c7' }};
                                    if (s.label) {{
                                        s.label.color = isDark ? '#38bdf8' : '#0369a1';
                                    }}
                                }}
                            }}

                            if (s.type === 'bar') {{
                                if (s.label) {{
                                    s.label.color = isDark ? '#f8fafc' : '#0f172a';
                                }}
                            }}

                            if (s.type === 'pie') {{
                                if (!s.itemStyle) s.itemStyle = {{}};
                                s.itemStyle.borderColor = isDark ? '#0f172a' : '#ffffff';
                            }}
                        }});
                    }}

                    return opt;
                }}

                function renderChart() {{
                    currentTheme = detectStreamlitTheme();
                    if (myChart) myChart.dispose();
                    myChart = echarts.init(chartDom, currentTheme === 'dark' ? 'dark' : null, {{ renderer: 'canvas' }});
                    var opt = JSON.parse(JSON.stringify(rawOption));
                    opt = applyThemeColors(opt, currentTheme);
                    opt.backgroundColor = 'transparent';
                    myChart.setOption(opt);
                }}

                renderChart();

                window.addEventListener('resize', function() {{
                    if (myChart) myChart.resize();
                }});

                if (window.matchMedia) {{
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {{
                        renderChart();
                    }});
                }}

                try {{
                    if (window.parent && window.parent.document) {{
                        var obs = new MutationObserver(function() {{
                            var newTheme = detectStreamlitTheme();
                            if (newTheme !== currentTheme) {{
                                renderChart();
                            }}
                        }});
                        obs.observe(window.parent.document.documentElement, {{ attributes: true, attributeFilter: ['data-theme', 'class'] }});
                        var appEl = window.parent.document.querySelector('.stApp');
                        if (appEl) {{
                            obs.observe(appEl, {{ attributes: true, attributeFilter: ['class', 'style'] }});
                        }}

                        setInterval(function() {{
                            var checkTheme = detectStreamlitTheme();
                            if (checkTheme !== currentTheme) {{
                                renderChart();
                            }}
                        }}, 700);
                    }}
                }} catch(e) {{}}
            }})();
        </script>
    </body>
    </html>
    """
    st.components.v1.html(html_code, height=height_px + 10)

# ==============================================================================
# 6. CARREGAMENTO E HIGIENIZAÇÃO DOS DADOS
# ==============================================================================
@st.cache_data(ttl=300, show_spinner="Consultando dados em tempo real da JFAL...")
def fetch_api_data() -> List[Dict[str, Any]]:
    url = "https://apiresidenciaadministrativa.jfal.jus.br/api/v1/execution"
    resp = requests.get(url, timeout=35)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=3600)
def load_brazil_geojson() -> Dict[str, Any]:
    with open("br_states.json", "r", encoding="utf-8") as f:
        geo = json.load(f)
    for feat in geo.get("features", []):
        feat["properties"]["name"] = feat.get("properties", {}).get("Estado", "")
    return geo

def process_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    df["timeStamp"] = pd.to_datetime(df["timeStamp"]).dt.tz_convert("America/Sao_Paulo")
    df["date"] = df["timeStamp"].dt.date
    df["data_str"] = df["timeStamp"].dt.strftime("%Y-%m-%d")
    df["duration_sec"] = pd.to_numeric(df["duration"], errors="coerce").fillna(1.0)
    df["state"] = df["state"].fillna("Não informado").replace({"": "Não informado"})
    df["filledByPDF"] = df["filledByPDF"].fillna(False).astype(bool)

    # Identificação amigável de simulador
    app_map = {
        "simulador_aposentadoria": "Simulador de Aposentadoria",
        "simulador_previdenciario": "Simulador Previdenciário"
    }
    df["app_label"] = df["applicationName"].map(lambda x: app_map.get(x, x))

    # Tarefas
    def clean_task(t):
        t_str = str(t).replace("{", "").replace("}", "").replace('"', '').strip()
        tasks = {
            "calculo_aposentadoria": "Cálculo de Aposentadoria",
            "simulador_previdenciario_rrc_jfal_creation": "Criação de RRC (JFAL)",
            "simulador_previdenciario_retirement_salary_calculation": "Salário de Aposentadoria",
            "simulador_previdenciario_rrc_creation": "Criação de RRC (Geral)"
        }
        return tasks.get(t_str, t_str.replace("_", " ").title())

    df["task_label"] = df["taskName"].apply(clean_task)

    # Órgãos normalizados
    def clean_agency(a):
        if not a or pd.isna(a) or str(a).strip() == "":
            return "Não informado"
        val = str(a).strip().upper()
        if val in ["NÃO INFORMADO", "NAO INFORMADO", "NONE", "NULL", "-"]:
            return "Não informado"
        if "JUSTIÇA FEDERAL EM ALAGOAS" in val or "JFAL" in val:
            return "JFAL (Justiça Federal em Alagoas)"
        if val in ["JUSTIÇA FEDERAL", "JF", "JUSTIÇA FEDERAL NA PARAÍBA", "JFPE", "JFCE", "JFSP", "TRF3", "TRF6", "TRF5", "TRF"]:
            return "Justiça Federal (Outras Seções/TRFs)"
        if "TRE" in val or "ELEITORAL" in val:
            return "Justiça Eleitoral (TRE/TSE)"
        if "TRT" in val or "TRABALHO" in val:
            return "Justiça do Trabalho (TRT/TST)"
        if "INSS" in val or "PREVIDENCIA" in val:
            return "INSS (Previdência Social)"
        if "MPU" in val or "MPF" in val:
            return "Ministério Público da União"
        if "UFRJ" in val or "UFMG" in val or "UFAL" in val or "UNIVERSIDADE" in val:
            return "Universidades Federais"
        if "IBAMA" in val:
            return "IBAMA"
        return val.title()

    df["agency_clean"] = df["agency"].apply(clean_agency)

    # Tempo e variáveis
    df["ano"] = df["timeStamp"].dt.year
    df["hora"] = df["timeStamp"].dt.hour
    df["hora_str"] = df["timeStamp"].dt.strftime("%H:00")
    df["dia_semana_num"] = df["timeStamp"].dt.dayofweek
    dias_pt = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
    df["dia_semana_nome"] = df["dia_semana_num"].map(dias_pt)

    return df

# ==============================================================================
# 7. FORMATAÇÃO E LÓGICA DE INTERVALOS
# ==============================================================================
def format_money(count: int) -> str:
    total = round(count * HORAS_POR_CALCULO * VALOR_HORA_TECNICA, 2)
    return f"R$ {int(total):_.0f}".replace("_", ".")

def format_hours(count: int) -> str:
    hours = count * HORAS_POR_CALCULO
    return f"{int(hours):_.0f} h".replace("_", ".")

def format_count(count: int) -> str:
    return f"{int(count):_.0f}".replace("_", ".")

def build_chronological_intervals(df: pd.DataFrame, interval_days: int, label_prefix: str):
    if df.empty:
        return []

    date_counts = df["date"].value_counts().to_dict()
    min_date = min(date_counts.keys())
    max_date = max(date_counts.keys())

    dias_semana_curtos = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    # Caso especial: Visão Geral (Todo o histórico)
    if label_prefix.lower() == "geral" or interval_days >= 90000:
        daily_records = []
        d = min_date
        total_interval_count = 0
        total_days = (max_date - min_date).days
        while d <= max_date:
            c = date_counts.get(d, 0)
            dia_semana = dias_semana_curtos[d.weekday()]
            daily_records.append({
                "date": d,
                "data_label": d.strftime("%d/%m/%y") if total_days > 90 else d.strftime("%d/%m"),
                "dia_label": dia_semana,
                "count": c
            })
            total_interval_count += c
            d += timedelta(days=1)

        nome_intervalo = f"Histórico Geral [{min_date.strftime('%d/%m/%Y')} - {max_date.strftime('%d/%m/%Y')}]"
        return [{
            "key": nome_intervalo,
            "number": 1,
            "start_date": min_date,
            "end_date": max_date,
            "total_count": total_interval_count,
            "daily_data": pd.DataFrame(daily_records)
        }]

    intervals = []
    curr_end = max_date
    total_span = (max_date - min_date).days
    total_intervals = total_span // interval_days + 1
    curr_num = total_intervals

    while curr_end >= min_date:
        curr_start = curr_end - timedelta(days=interval_days - 1)
        if curr_start < min_date:
            curr_start = min_date

        daily_records = []
        d = curr_start
        total_interval_count = 0
        interval_span = (curr_end - curr_start).days
        while d <= curr_end:
            c = date_counts.get(d, 0)
            dia_semana = dias_semana_curtos[d.weekday()]
            daily_records.append({
                "date": d,
                "data_label": d.strftime("%d/%m/%y") if interval_span > 90 else d.strftime("%d/%m"),
                "dia_label": dia_semana,
                "count": c
            })
            total_interval_count += c
            d += timedelta(days=1)

        nome_intervalo = f"{label_prefix} {curr_num} [{curr_start.strftime('%d/%m')} - {curr_end.strftime('%d/%m/%Y')}]"

        intervals.append({
            "key": nome_intervalo,
            "number": curr_num,
            "start_date": curr_start,
            "end_date": curr_end,
            "total_count": total_interval_count,
            "daily_data": pd.DataFrame(daily_records)
        })

        curr_end = curr_start - timedelta(days=1)
        curr_num -= 1

    return intervals

# ==============================================================================
# 8. INICIALIZAÇÃO DOS DADOS
# ==============================================================================
try:
    raw_data = fetch_api_data()
    df_all = process_dataframe(raw_data)
    brazil_geojson = load_brazil_geojson()
except Exception as e:
    st.error(f"Erro ao carregar dados da API: {e}")
    st.stop()

# ==============================================================================
# 9. BARRA LATERAL: FILTROS CLAROS E OBJETIVOS (SEM SELECT DE ESTILO DE MAPA)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Filtros do Painel")

    # 1. Fase dos Dados
    filtro_fase = st.selectbox(
        "Fase dos Dados",
        ("Aberto ao público", "Dados totais", "Com token"),
        help="Aberto ao público considera registros após 26/08/2024."
    )

    df_filtered = df_all.copy()
    if filtro_fase == "Aberto ao público":
        df_filtered = df_filtered[df_filtered["date"] >= CUTOFF_DATE]
    elif filtro_fase == "Com token":
        df_filtered = df_filtered[df_filtered["date"] < CUTOFF_DATE]

    # 2. Simulador / Aplicação
    app_options = ["Todos os Simuladores"] + sorted(df_filtered["app_label"].unique().tolist())
    selected_app = st.selectbox("Simulador / Aplicação", app_options)
    if selected_app != "Todos os Simuladores":
        df_filtered = df_filtered[df_filtered["app_label"] == selected_app]

    # 3. Estado (UF)
    states = ["Geral"] + sorted([s for s in df_filtered["state"].unique() if s != "Não informado"])
    selected_state = st.selectbox("Estado Federativo (UF)", states)
    if selected_state != "Geral":
        df_filtered = df_filtered[df_filtered["state"] == selected_state]

    # 4. Agrupamento Temporal
    filter_option = st.selectbox(
        "Agrupar períodos por",
        ("Por semana", "Por mês", "Por trimestre", "Por semestre", "Por ano", "Geral")
    )
    days_map = {
        "Por semana": 7,
        "Por mês": 30,
        "Por trimestre": 90,
        "Por semestre": 180,
        "Por ano": 365,
        "Geral": 99999
    }
    interval_days = days_map[filter_option]
    type_label = filter_option.replace("Por ", "").capitalize()

    # Gera os intervalos cronológicos
    interval_list = build_chronological_intervals(df_filtered, interval_days, type_label)
    if not interval_list:
        st.warning("Nenhum dado encontrado para o filtro selecionado.")
        st.stop()

    interval_keys = [item["key"] for item in interval_list]
    selected_interval_key = st.selectbox("Selecione o Período", interval_keys, index=0)

    curr_idx = interval_keys.index(selected_interval_key)
    curr_interval = interval_list[curr_idx]
    prev_interval = interval_list[curr_idx + 1] if curr_idx + 1 < len(interval_list) else None

    st.markdown("---")
    if st.button("🔄 Atualizar Dados da API", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==============================================================================
# 10. CABEÇALHO INSTITUCIONAL
# ==============================================================================
st.markdown(
    f"""
    <div class="jfal-header">
        <div>
            <h1 class="jfal-header-title">Calculadora Previdenciária • Justiça Federal em Alagoas</h1>
            <p class="jfal-header-sub">Painel Executivo de Impacto Econômico, Celeridade Processual e Produtividade das Simulações</p>
        </div>
        <div>
            <span class="jfal-badge">JFAL • Residência em TI</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 11. SEÇÃO 1: CARDS EXECUTIVOS DO PERÍODO SELECIONADO (5 CARDS OBJETIVOS)
# ==============================================================================
st.markdown(
    f"<div class='section-title'>📌 {selected_state}: {selected_interval_key} <span style='font-size: 0.9rem; font-weight: normal; opacity: 0.7;'>({filtro_fase})</span></div>",
    unsafe_allow_html=True
)
st.caption("Visão consolidada dos ganhos de produtividade e economia gerados pelas simulações executadas no período selecionado.")

calculos_periodo = curr_interval["total_count"]
calculos_anterior = prev_interval["total_count"] if prev_interval else 0

delta_text = None
if prev_interval and calculos_anterior > 0:
    delta_pct = ((calculos_periodo / calculos_anterior) - 1) * 100
    delta_text = f"{delta_pct:+.1f}% vs anterior"

df_period_slice = df_filtered[
    (df_filtered["date"] >= curr_interval["start_date"]) &
    (df_filtered["date"] <= curr_interval["end_date"])
]

dias_no_periodo = max((curr_interval["end_date"] - curr_interval["start_date"]).days + 1, 1)
media_diaria = calculos_periodo / dias_no_periodo

chart_daily_calc = curr_interval["daily_data"]
pico_dia = chart_daily_calc.loc[chart_daily_calc["count"].idxmax()] if not chart_daily_calc.empty else None
pico_data_label = f"{pico_dia['dia_label']} ({pico_dia['data_label']})" if pico_dia is not None else "-"
pico_val = int(pico_dia["count"]) if pico_dia is not None else 0

# Exibição dos 5 cards principais
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">💳 Impacto Econômico</div>
            <div class="metric-val">{format_money(calculos_periodo)}</div>
            <div class="metric-sub">{delta_text or 'Economia aos cofres'}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">⏱️ Custo de Oportunidade</div>
            <div class="metric-val">{format_hours(calculos_periodo)}</div>
            <div class="metric-sub">Horas poupadas de peritos</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">🖱️ Cálculos Realizados</div>
            <div class="metric-val">{format_count(calculos_periodo)}</div>
            <div class="metric-sub">{delta_text or 'Simulações no período'}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">📊 Ritmo: Média Diária</div>
            <div class="metric-val">{media_diaria:.1f}</div>
            <div class="metric-sub">Simulações/dia no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with k5:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">🚀 Pico no Período</div>
            <div class="metric-val">{format_count(pico_val)}</div>
            <div class="metric-sub">Em {pico_data_label}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==============================================================================
# SEÇÃO ESPECIAL: COMPARATIVO ENTRE OPERAÇÕES (TASKNAMES) DO SIMULADOR PREVIDENCIÁRIO
# ==============================================================================
is_previdenciario = (
    selected_app in ["Simulador Previdenciário", "simulador_previdenciario"]
    or "Previdenciário" in selected_app
)

if is_previdenciario:
    st.markdown(
        "<div class='section-title'>⚖️ Comparativo de Operações (TaskNames) • Simulador Previdenciário</div>",
        unsafe_allow_html=True
    )
    st.caption(
        "Detalhamento comparativo entre as diferentes modalidades de simulação executadas pelo módulo Previdenciário "
        "(Criação de RRC - JFAL, Criação de RRC - Geral e Cálculo de Salário de Aposentadoria)."
    )

    # 1. Cards de Resumo por Tarefa no Período Selecionado
    task_counts_period = df_period_slice["task_label"].value_counts()
    task_colors_map = {
        "Criação de RRC (JFAL)": "#0284c7",
        "Salário de Aposentadoria": "#10b981",
        "Criação de RRC (Geral)": "#f59e0b"
    }

    prev_tasks = ["Criação de RRC (JFAL)", "Salário de Aposentadoria", "Criação de RRC (Geral)"]
    cols_tasks = st.columns(len(prev_tasks))

    for idx, t_name in enumerate(prev_tasks):
        cnt = int(task_counts_period.get(t_name, 0))
        pct = (cnt / calculos_periodo * 100) if calculos_periodo > 0 else 0
        with cols_tasks[idx]:
            st.markdown(
                f"""
                <div class="metric-card-box" style="border-left: 4px solid {task_colors_map.get(t_name, '#38bdf8')};">
                    <div class="metric-title">📋 {t_name}</div>
                    <div class="metric-val" style="font-size: 1.5rem; color: {task_colors_map.get(t_name, '#0284c7')};">{format_count(cnt)} <span style="font-size: 0.85rem; font-weight: 500; opacity: 0.8;">({pct:.1f}%)</span></div>
                    <div class="metric-sub">{format_money(cnt)} economizados • {format_hours(cnt)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 2. Gráficos Comparativos: Donut de Distribuição & Barras de Volume/Impacto
    c_prev_g1, c_prev_g2 = st.columns([1, 1])

    with c_prev_g1:
        st.markdown("##### 🍩 Distribuição & Participação por Operação")
        st.caption("Proporção percentual de cada tarefa no período selecionado.")

        donut_task_data = [
            {"value": int(task_counts_period.get(t, 0)), "name": t, "itemStyle": {"color": task_colors_map.get(t, "#38bdf8")}}
            for t in prev_tasks if int(task_counts_period.get(t, 0)) > 0
        ]
        if not donut_task_data:
            donut_task_data = [{"value": 0, "name": "Sem registros", "itemStyle": {"color": "#64748b"}}]

        donut_task_opts = {
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}<br/>Simulações: <b>{c}</b> ({d}%)"
            },
            "legend": {
                "bottom": "5%",
                "left": "center"
            },
            "series": [
                {
                    "type": "pie",
                    "radius": ["45%", "70%"],
                    "avoidLabelOverlap": False,
                    "itemStyle": {
                        "borderRadius": 8,
                        "borderColor": "rgba(0, 0, 0, 0.2)",
                        "borderWidth": 2
                    },
                    "label": {"show": False},
                    "emphasis": {
                        "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
                    },
                    "data": donut_task_data
                }
            ]
        }
        render_echarts(donut_task_opts, height="320px", key="donut_prev_tasks_echarts")

    with c_prev_g2:
        st.markdown("##### 📊 Comparativo de Volume & Impacto Financeiro")
        st.caption("Comparação direta do volume e valor econômico poupado por cada tarefa.")

        tasks_bar_labels = [t for t in prev_tasks if int(task_counts_period.get(t, 0)) > 0]
        if not tasks_bar_labels:
            tasks_bar_labels = prev_tasks
        tasks_bar_vals = [int(task_counts_period.get(t, 0)) for t in tasks_bar_labels]

        bar_task_opts = {
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "formatter": "{b}<br/>Simulações: <b>{c}</b>"
            },
            "grid": {"left": "3%", "right": "12%", "bottom": "8%", "top": "8%", "containLabel": True},
            "xAxis": {"type": "value", "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "category", "data": tasks_bar_labels, "axisLabel": {"fontWeight": "600", "fontSize": 12}},
            "series": [
                {
                    "type": "bar",
                    "data": [
                        {"value": v, "itemStyle": {"color": task_colors_map.get(t, "#0284c7"), "borderRadius": [0, 6, 6, 0]}}
                        for t, v in zip(tasks_bar_labels, tasks_bar_vals)
                    ],
                    "label": {
                        "show": True,
                        "position": "right",
                        "formatter": "{c}",
                        "fontWeight": "bold"
                    }
                }
            ]
        }
        render_echarts(bar_task_opts, height="320px", key="bar_prev_tasks_echarts")

    # 3. Evolução Temporal Comparada por Tarefa (Multi-Linha)
    st.markdown("##### 📈 Evolução Temporal Diária Comparativa por Tarefa")
    st.caption("Acompanhe o ritmo diário e identifique momentos de pico de cada operação no período selecionado.")

    daily_task_df = df_period_slice.groupby(["date", "task_label"]).size().unstack(fill_value=0)
    dates_series = curr_interval["daily_data"]["date"].tolist()
    labels_task_x = [f"{row['dia_label']} ({row['data_label']})" if filter_option == "Por semana" else row["data_label"] for _, row in curr_interval["daily_data"].iterrows()]

    series_task_lines = []
    for t in prev_tasks:
        if t in daily_task_df.columns:
            vals = [int(daily_task_df.loc[d, t]) if d in daily_task_df.index else 0 for d in dates_series]
        else:
            vals = [0] * len(dates_series)

        series_task_lines.append({
            "name": t,
            "type": "line",
            "smooth": True,
            "data": vals,
            "itemStyle": {"color": task_colors_map.get(t, "#38bdf8")},
            "lineStyle": {"width": 2.5}
        })

    line_tasks_opts = {
        "tooltip": {
            "trigger": "axis"
        },
        "legend": {
            "data": prev_tasks,
            "top": "top",
            "textStyle": {"fontSize": 12}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "16%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": labels_task_x,
            "boundaryGap": filter_option != "Por semana",
            "axisLabel": {"fontWeight": "500", "fontSize": 11}
        },
        "yAxis": {
            "type": "value",
            "name": "Execuções",
            "splitLine": {"lineStyle": {"type": "dashed"}}
        },
        "series": series_task_lines
    }
    if len(labels_task_x) > 35:
        line_tasks_opts["dataZoom"] = [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "show": True, "bottom": "0%", "height": 18}
        ]
        line_tasks_opts["grid"]["bottom"] = "18%"

    render_echarts(line_tasks_opts, height="340px", key="line_tasks_comparison_echarts")

    # 4. Tabela Resumo Comparativa das Tarefas
    st.markdown("##### 📋 Tabela Sintética Comparativa das Tarefas Previdenciárias")
    table_data = []
    for t in prev_tasks:
        cnt = int(task_counts_period.get(t, 0))
        pct = (cnt / calculos_periodo * 100) if calculos_periodo > 0 else 0
        df_t = df_period_slice[df_period_slice["task_label"] == t]
        dur_med = df_t["duration_sec"].mean() if not df_t.empty else 0.0
        cnt_total_hist = int((df_filtered["task_label"] == t).sum())

        table_data.append({
            "Operação / Tarefa (TaskName)": t,
            "Execuções no Período": cnt,
            "Participação (%)": f"{pct:.1f}%",
            "Impacto Econômico": format_money(cnt),
            "Horas Poupadas": format_hours(cnt),
            "Duração Média": f"{dur_med:.1f}s",
            "Total Histórico Acumulado": cnt_total_hist
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
    st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

# ==============================================================================
# 12. SEÇÃO 2: EVOLUÇÃO TEMPORAL NO PERÍODO (COM MÉDIA MÓVEL 7D)
# ==============================================================================
st.markdown("<div class='section-title'>📈 Evolução Diária no Período Selecionado</div>", unsafe_allow_html=True)
st.caption("A linha azul destaca a quantidade de cálculos em cada dia. A linha dourada representa a **Média Móvel de 7 dias**, que suaviza as oscilações de finais de semana e expõe a tendência real de uso.")

chart_daily = curr_interval["daily_data"].copy()
chart_daily["media_movel"] = chart_daily["count"].rolling(window=7, min_periods=1).mean().round(1)

labels_x = [f"{row['dia_label']} ({row['data_label']})" if filter_option == "Por semana" else row["data_label"] for _, row in chart_daily.iterrows()]
vals_y = chart_daily["count"].tolist()
mm_y = chart_daily["media_movel"].tolist()

line_opts = {
    "tooltip": {
        "trigger": "axis",
        "formatter": "{b}<br/>Cálculos realizados: <b>{c}</b>"
    },
    "legend": {
        "data": ["Cálculos Realizados", "Média Móvel (7 dias)"],
        "top": "top",
        "textStyle": {"fontSize": 13}
    },
    "toolbox": {
        "feature": {
            "magicType": {"type": ["line", "bar"], "title": {"line": "Linha", "bar": "Barras"}},
            "saveAsImage": {"title": "Salvar Imagem", "pixelRatio": 2}
        }
    },
    "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "15%", "containLabel": True},
    "xAxis": {
        "type": "category",
        "boundaryGap": filter_option != "Por semana",
        "data": labels_x,
        "axisLabel": {"fontWeight": "500", "fontSize": 12}
    },
    "yAxis": {
        "type": "value",
        "name": "Execuções",
        "splitLine": {"lineStyle": {"type": "dashed"}}
    },
    "series": [
        {
            "name": "Cálculos Realizados",
            "type": "line",
            "smooth": True,
            "data": vals_y,
            "itemStyle": {"color": "#38bdf8"},
            "lineStyle": {"width": 3.5},
            "areaStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "rgba(56, 189, 248, 0.45)"},
                        {"offset": 1, "color": "rgba(56, 189, 248, 0.02)"}
                    ]
                }
            },
            "label": {
                "show": True,
                "position": "top",
                "formatter": "{c}",
                "fontWeight": "bold",
                "fontSize": 12
            }
        },
        {
            "name": "Média Móvel (7 dias)",
            "type": "line",
            "smooth": True,
            "data": mm_y,
            "itemStyle": {"color": "#f59e0b"},
            "lineStyle": {"width": 2.5, "type": "dashed"}
        }
    ]
}
if len(labels_x) > 35:
    line_opts["dataZoom"] = [
        {"type": "inside", "start": 0, "end": 100},
        {"type": "slider", "show": True, "bottom": "0%", "height": 18}
    ]
    line_opts["grid"]["bottom"] = "18%"

render_echarts(line_opts, height="360px", key="period_line_echarts")

# ==============================================================================
# 13. SEÇÃO 3: MAPA DO BRASIL AMPLO E GEOGRÁFICO (ADAPTAÇÃO AUTOMÁTICA DE TEMA)
# ==============================================================================
st.markdown("<div class='section-title'>🗺️ Distribuição Geográfica de Cálculos no Brasil</div>", unsafe_allow_html=True)
st.caption("Mapa geográfico interativo no padrão original da JFAL, exibido em tamanho amplo com cartografia real e adaptação automática ao tema Light / Dark.")

df_map_data = df_period_slice[df_period_slice["state"] != "Não informado"]
map_state_counts = df_map_data.groupby("state").size().reset_index(name="Execuções")
map_state_counts["Impacto"] = map_state_counts["Execuções"].apply(lambda x: format_money(x))
map_state_counts["Horas"] = map_state_counts["Execuções"].apply(lambda x: format_hours(x))

if not map_state_counts.empty:
    map_func = getattr(px, 'choropleth_map', getattr(px, 'choropleth_mapbox', None))

    # Detecta tema de forma 100% automática sem exigir select no sidebar
    current_detected_theme = get_current_theme()
    is_dark_map = (current_detected_theme == "dark")
    auto_style = "carto-darkmatter" if is_dark_map else "carto-positron"
    auto_template = "plotly_dark" if is_dark_map else "plotly_white"

    fig_args = {
        "data_frame": map_state_counts,
        "geojson": brazil_geojson,
        "locations": "state",
        "featureidkey": "properties.Estado",
        "color": "Execuções",
        "color_continuous_scale": "Blues",
        "zoom": 3.4,
        "center": {"lat": -14.2350, "lon": -51.9253},
        "opacity": 0.85,
        "hover_name": "state",
        "hover_data": {
            "state": False,
            "Execuções": True,
            "Impacto": True,
            "Horas": True
        },
        "labels": {"Execuções": "Cálculos Realizados", "state": "Estado"}
    }

    if hasattr(px, 'choropleth_map'):
        fig_args['map_style'] = auto_style
    else:
        fig_args['mapbox_style'] = auto_style

    fig_map = map_func(**fig_args)
    fig_map.update_layout(
        template=auto_template,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=560,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_colorbar=dict(
            title=dict(
                text="Cálculos",
                font=dict(color="#cbd5e1" if is_dark_map else "#1e293b")
            ),
            tickfont=dict(color="#cbd5e1" if is_dark_map else "#1e293b"),
            thickness=16,
            len=0.75,
            x=0.02,
            y=0.5
        )
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Destaques dos Top 5 Estados abaixo do Mapa
    top5_df = map_state_counts.sort_values("Execuções", ascending=False).head(5)
    cols_top = st.columns(5)
    for idx, (_, r) in enumerate(top5_df.iterrows()):
        pct_state = (r["Execuções"] / calculos_periodo * 100) if calculos_periodo > 0 else 0
        with cols_top[idx]:
            st.metric(
                label=f"#{idx+1} {r['state']}",
                value=format_count(r["Execuções"]),
                delta=f"{pct_state:.1f}% do total"
            )
else:
    st.info("Nenhum registro com estado informado no período selecionado.")

# ==============================================================================
# 14. SEÇÃO 4: HÁBITOS DE USO E HORÁRIOS DE PICO (2 COLUNAS INTEGRADAS)
# ==============================================================================
st.markdown("<div class='section-title'>⏱️ Padrões Operacionais & Horários de Pico</div>", unsafe_allow_html=True)
st.caption("Cruzamento analítico do momento exato das simulações. Identifique os horários e dias de maior sobrecarga e demanda técnica.")

c_heat1, c_heat2 = st.columns([3, 2])

with c_heat1:
    st.markdown("##### 📅 Concentração de Acessos: Dia da Semana × Horário")
    st.caption("Mapa de calor estilo 'Punch Card'. Cores mais intensas revelam os momentos de maior atividade forense.")

    dias_semana_ordem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    horas_lista = [f"{h:02d}h" for h in range(24)]

    pivot_heat = df_period_slice.groupby(["dia_semana_nome", "hora"]).size().reset_index(name="count")
    punch_data = []
    max_punch_val = int(pivot_heat["count"].max()) if not pivot_heat.empty else 10

    for _, row in pivot_heat.iterrows():
        try:
            d_idx = dias_semana_ordem.index(row["dia_semana_nome"])
            h_idx = int(row["hora"])
            val = int(row["count"])
            punch_data.append([h_idx, d_idx, val])
        except Exception:
            continue

    punch_opts = {
        "tooltip": {
            "position": "top",
            "formatter": "{c} cálculos realizados"
        },
        "grid": {"top": "12%", "left": "8%", "right": "4%", "bottom": "18%"},
        "xAxis": {
            "type": "category",
            "data": horas_lista,
            "splitArea": {"show": True},
            "axisLabel": {"interval": 1}
        },
        "yAxis": {
            "type": "category",
            "data": dias_semana_ordem,
            "splitArea": {"show": True},
            "axisLabel": {"fontWeight": "bold"}
        },
        "visualMap": {
            "min": 0,
            "max": max_punch_val,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
            "inRange": {
                "color": ["#1e293b", "#0284c7", "#38bdf8", "#10b981", "#fbbf24"]
            }
        },
        "series": [
            {
                "type": "heatmap",
                "data": punch_data,
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}}
            }
        ]
    }
    render_echarts(punch_opts, height="380px", key="punch_card_heatmap")

with c_heat2:
    st.markdown("##### 🕒 Volume Total por Faixa Horária (00h às 23h)")
    st.caption("Distribuição direta do volume acumulado ao longo das 24 horas do dia no período.")

    hour_counts = df_period_slice.groupby("hora_str").size().reset_index(name="count")
    all_24h = [f"{h:02d}:00" for h in range(24)]
    hour_counts = hour_counts.set_index("hora_str").reindex(all_24h, fill_value=0).reset_index()

    bar_hour_opts = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "14%", "top": "12%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": hour_counts["hora_str"].tolist(),
            "axisLabel": {"interval": 2, "rotate": 45}
        },
        "yAxis": {
            "type": "value",
            "splitLine": {"lineStyle": {"type": "dashed"}}
        },
        "series": [
            {
                "type": "bar",
                "data": hour_counts["count"].tolist(),
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#38bdf8"},
                            {"offset": 1, "color": "#1e3a8a"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0]
                }
            }
        ]
    }
    render_echarts(bar_hour_opts, height="380px", key="bar_hours_chart")

# ==============================================================================
# 15. SEÇÃO 5: PERFIL DAS DEMANDAS & FORMA DE ENTRADA (AUTO-EXPLICATIVO)
# ==============================================================================
st.markdown("<div class='section-title'>📄 Modalidade de Entrada & Órgãos Usuários</div>", unsafe_allow_html=True)
st.caption("Entenda como os usuários realizam as simulações e quais instituições públicas mais utilizam a calculadora.")

c_mod1, c_mod2 = st.columns([1, 1])

with c_mod1:
    st.markdown("##### 📎 Forma de Entrada dos Dados (PDF do SARH vs Digitação)")
    st.caption("💡 **O que significa:** No simulador, o usuário pode anexar o **Extrato em PDF do sistema SARH** (leitura e importação automática dos dados funcionais) ou realizar a **Digitação Manual** campo a campo.")

    pdf_status = df_period_slice["filledByPDF"].value_counts().to_dict()
    com_pdf = pdf_status.get(True, 0)
    sem_pdf = pdf_status.get(False, 0)

    mod_data = [
        {"value": com_pdf, "name": "Importação via PDF do SARH (Automático)", "itemStyle": {"color": "#10b981"}},
        {"value": sem_pdf, "name": "Preenchimento Manual de Dados", "itemStyle": {"color": "#0284c7"}}
    ]

    donut_opts = {
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}<br/>Cálculos: <b>{c}</b> ({d}%)"
        },
        "legend": {
            "bottom": "5%",
            "left": "center"
        },
        "series": [
            {
                "type": "pie",
                "radius": ["45%", "70%"],
                "avoidLabelOverlap": False,
                "itemStyle": {
                    "borderRadius": 8,
                    "borderColor": "rgba(0, 0, 0, 0.2)",
                    "borderWidth": 2
                },
                "label": {"show": False},
                "emphasis": {
                    "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
                },
                "data": mod_data
            }
        ]
    }
    render_echarts(donut_opts, height="340px", key="donut_modalidade_pdf")

with c_mod2:
    st.markdown("##### 🏛️ Principais Órgãos e Tribunais Demandantes")
    st.caption("💡 Instituições e órgãos do Judiciário e Executivo Federal de onde partiram as requisições de cálculo.")

    agency_data = df_period_slice[df_period_slice["agency_clean"] != "Não informado"].groupby("agency_clean").size().reset_index(name="count")
    top_agencies = agency_data.sort_values("count", ascending=True).tail(6)

    if not top_agencies.empty:
        agency_opts = {
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"}
            },
            "grid": {"left": "3%", "right": "12%", "bottom": "5%", "top": "5%", "containLabel": True},
            "xAxis": {"type": "value", "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "category", "data": top_agencies["agency_clean"].tolist(), "axisLabel": {"fontSize": 12}},
            "series": [
                {
                    "type": "bar",
                    "data": top_agencies["count"].tolist(),
                    "itemStyle": {
                        "color": "#38bdf8",
                        "borderRadius": [0, 6, 6, 0]
                    },
                    "label": {
                        "show": True,
                        "position": "right",
                        "fontWeight": "bold"
                    }
                }
            ]
        }
        render_echarts(agency_opts, height="340px", key="top_agencies_chart")
    else:
        st.info("Nenhum órgão específico identificado nos registros deste período.")

st.markdown("<div class='divider-line'></div>", unsafe_allow_html=True)

# ==============================================================================
# 16. SEÇÃO 6: PANORAMA GERAL HISTÓRICO & CALENDÁRIO ANUAL (3 CARDS TOTAIS)
# ==============================================================================
st.markdown("<div class='section-title'>🌐 Panorama Geral Acumulado (Todo o Histórico)</div>", unsafe_allow_html=True)
st.caption("Totais absolutos desde o início das operações da calculadora na Justiça Federal em Alagoas.")

total_acumulado = len(df_filtered)

pg1, pg2, pg3 = st.columns(3)

with pg1:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">💳 Impacto Econômico Histórico</div>
            <div class="metric-val" style="color: #0284c7;">{format_money(total_acumulado)}</div>
            <div class="metric-sub">Economia estimada acumulada</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with pg2:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">⏱️ Horas Técnicas Economizadas</div>
            <div class="metric-val" style="color: #0284c7;">{format_hours(total_acumulado)}</div>
            <div class="metric-sub">Trabalho técnico/pericial poupado</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with pg3:
    st.markdown(
        f"""
        <div class="metric-card-box">
            <div class="metric-title">🖱️ Total Geral de Cálculos</div>
            <div class="metric-val" style="color: #0284c7;">{format_count(total_acumulado)}</div>
            <div class="metric-sub">Simulações processadas no histórico</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Calendário Anual Heatmap (GitHub Style)
st.markdown("##### 📅 Calendário Anual de Atividade Contínua")
st.caption("Intensidade diária de uso da ferramenta em cada dia do ano civil selecionado. Quadrantes mais brilhantes indicam dias de pico.")

anos_disponiveis = sorted(df_filtered["ano"].unique().tolist(), reverse=True)
if not anos_disponiveis:
    anos_disponiveis = [datetime.date.today().year]

col_ano_sel, _ = st.columns([2, 5])
with col_ano_sel:
    ano_calendario = st.selectbox("Selecione o Ano do Calendário:", anos_disponiveis, index=0)

df_ano_cal = df_filtered[df_filtered["ano"] == ano_calendario]
cal_daily_counts = df_ano_cal.groupby("data_str").size().reset_index(name="count")
cal_series_data = [[row["data_str"], int(row["count"])] for _, row in cal_daily_counts.iterrows()]
max_cal = int(cal_daily_counts["count"].max()) if not cal_daily_counts.empty else 100

cal_opts = {
    "tooltip": {
        "position": "top",
        "formatter": "{c} cálculos realizados"
    },
    "visualMap": {
        "min": 0,
        "max": max_cal,
        "calculable": True,
        "orient": "horizontal",
        "left": "center",
        "bottom": "0%",
        "inRange": {
            "color": ["#1e293b", "#0369a1", "#0284c7", "#38bdf8", "#10b981"]
        }
    },
    "calendar": {
        "top": 45,
        "left": 40,
        "right": 40,
        "cellSize": ["auto", 18],
        "range": str(ano_calendario),
        "itemStyle": {
            "borderWidth": 1
        },
        "yearLabel": {"show": False},
        "dayLabel": {
            "firstDay": 1,
            "nameMap": ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        },
        "monthLabel": {
            "nameMap": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        }
    },
    "series": [
        {
            "type": "heatmap",
            "coordinateSystem": "calendar",
            "data": cal_series_data
        }
    ]
}
render_echarts(cal_opts, height="240px", key=f"calendar_year_{ano_calendario}")

# Histórico das Últimas Semanas / Meses / Semestres / Anos
if len(interval_list) > 1:
    st.markdown(f"##### 📊 Histórico Comparativo dos Últimos Períodos ({type_label})")
    st.caption("Evolução ordenada cronologicamente dos períodos mais recentes.")

    recent_intervals = interval_list[:8][::-1]
    labels_hist = [item["key"].split(" [")[0] for item in recent_intervals]
    values_hist = [item["total_count"] for item in recent_intervals]

    bar_hist_opts = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "grid": {"left": "3%", "right": "10%", "bottom": "5%", "top": "5%", "containLabel": True},
        "xAxis": {"type": "value", "splitLine": {"lineStyle": {"type": "dashed"}}},
        "yAxis": {"type": "category", "data": labels_hist, "axisLabel": {"fontWeight": "bold"}},
        "series": [
            {
                "type": "bar",
                "data": values_hist,
                "itemStyle": {
                    "color": "#0284c7",
                    "borderRadius": [0, 6, 6, 0]
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{c}",
                    "fontWeight": "bold"
                }
            }
        ]
    }
    render_echarts(bar_hist_opts, height="320px", key="historico_ultimos_periodos_clean")

# ==============================================================================
# 17. SEÇÃO 7: AUDITORIA & EXPORTAÇÃO DE DADOS (EXPANSÍVEL)
# ==============================================================================
with st.expander("📋 Ver Tabela de Dados Granulares e Exportar Relatório CSV"):
    st.markdown("Consulte os registros individuais processados no período para auditoria ou realize o download em planilha:")

    c_search, c_btn = st.columns([3, 1])
    with c_search:
        busca = st.text_input("🔍 Pesquisar nos registros:", placeholder="Digite estado, simulador, órgão...")

    df_export = df_period_slice[[
        "id", "timeStamp", "app_label", "task_label", "state", "agency_clean",
        "filledByPDF", "duration_sec"
    ]].copy()

    df_export = df_export.rename(columns={
        "id": "ID",
        "timeStamp": "Data/Hora",
        "app_label": "Simulador",
        "task_label": "Operação",
        "state": "Estado (UF)",
        "agency_clean": "Órgão Identificado",
        "filledByPDF": "Entrada via PDF",
        "duration_sec": "Duração (s)"
    })

    if busca:
        termo = busca.lower()
        mask = df_export.astype(str).apply(lambda row: row.str.lower().str.contains(termo).any(), axis=1)
        df_export = df_export[mask]

    st.dataframe(df_export.head(300), use_container_width=True, hide_index=True)

    with c_btn:
        csv_file = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar Dados (CSV)",
            data=csv_file,
            file_name=f"calculadora_jfal_{curr_interval['start_date']}_{curr_interval['end_date']}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==============================================================================
# FIM DO DASHBOARD APP_V3
# ==============================================================================
