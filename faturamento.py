import pandas as pd
from datetime import datetime, timedelta
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 🔐 PROTEÇÃO DE ACESSO
# ==========================================
st.set_page_config(page_title="Dashboard Comercial - PAPAPÁ", layout="wide", initial_sidebar_state="expanded")

CODIGO_ACESSO = "Papapapa#@12"
token_hoje = f"access_comercial_{datetime.now().strftime('%Y%m%d')}"

if st.query_params.get("auth") != token_hoje:
    st.title("🔐 Acesso Restrito - Comercial Papapá")
    codigo_digitado = st.text_input("Digite a senha de acesso", type="password")
    if st.button("Entrar"):
        if codigo_digitado == CODIGO_ACESSO:
            st.query_params["auth"] = token_hoje
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# ==========================================
# 📊 CARREGAMENTO E TRATAMENTO
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        arquivo = "dados_performance 1.xlsx"
        df_g = pd.read_excel(arquivo, sheet_name="Geral")
        df_v = pd.read_excel(arquivo, sheet_name="Vendedores")
        
        df_g['Data'] = pd.to_datetime(df_g['Data']).dt.date
        df_v['Data'] = pd.to_datetime(df_v['Data']).dt.date
        return df_g, df_v
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None, None

df_geral_hist, df_vendedores_hist = carregar_dados()

# --- FERIADOS ---
class FeriadosBrasil(AbstractHolidayCalendar):
    rules = [
        Holiday('Confraternização Universal', month=1, day=1),
        Holiday('Tiradentes', month=4, day=21),
        Holiday('Dia do Trabalho', month=5, day=1),
        Holiday('Independência', month=9, day=7),
        Holiday('Nossa Sra Aparecida', month=10, day=12),
        Holiday('Finados', month=11, day=2),
        Holiday('Proclamação da República', month=11, day=15),
        Holiday('Natal', month=12, day=25),
    ]

cal = FeriadosBrasil()
feriados_pandas = cal.holidays(start='2026-01-01', end='2026-12-31')
lista_feriados = [d.date() for d in feriados_pandas]

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Filtro")
    data_selecionada = st.date_input("Data de referência:", value=datetime(2026, 4, 16).date(), format="DD/MM/YYYY")

# ==========================================
# 📝 LÓGICA DE DATAS (D-1 ÚTIL)
# ==========================================
inicio_mes = data_selecionada.replace(day=1)
fim_mes_civil = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
dias_uteis_reais = [d.date() for d in pd.date_range(inicio_mes, fim_mes_civil, freq='B') if d.date() not in lista_feriados]

data_limite_faturamento = dias_uteis_reais[-4] if len(dias_uteis_reais) > 4 else dias_uteis_reais[-1]
dias_uteis_totais_list = [d for d in dias_uteis_reais if d <= data_limite_faturamento]
dias_uteis_comerciais_totais = len(dias_uteis_totais_list)

dias_uteis_anteriores = [d for d in dias_uteis_totais_list if d < data_selecionada]
dias_uteis_passados = len(dias_uteis_anteriores)
data_ref_calculo = dias_uteis_anteriores[-1] if dias_uteis_passados > 0 else inicio_mes

dias_uteis_restantes = len([d for d in dias_uteis_totais_list if d >= data_selecionada])
percentual_esperado = (dias_uteis_passados / dias_uteis_comerciais_totais) * 100 if dias_uteis_comerciais_totais > 0 else 100

def fmt_br(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt_m(v): return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# 📝 BLOCO 1: PERFORMANCE GERAL
# ==========================================
if df_geral_hist is not None:
    linha_g = df_geral_hist[df_geral_hist['Data'] == data_selecionada]
    if not linha_g.empty:
        rg = linha_g.iloc[0]
        meta_g = float(rg['Meta_Mes'])
        fat_g = float(rg['Faturado_Acumulado'])
        dig_g = float(rg['Digitado_Acumulado'])
        dev_g = abs(float(rg.get('Devolucoes', 0)))

        total_liq_g = (fat_g + dig_g) - dev_g
        perc_g = (total_liq_g / meta_g * 100) if meta_g > 0 else 0
        gap_g = perc_g - percentual_esperado
        falta_g = max(meta_g - total_liq_g, 0)
        ritmo_g = (falta_g / dias_uteis_restantes) if dias_uteis_restantes > 0 else 0

        st.subheader(f"📊 Resultado Consolidado - Papapá (Ref: {data_ref_calculo.strftime('%d/%m')})")
        
        c1, c2, c3, c_dev, c_total, c4, c5 = st.columns(7)
        with c1: st.metric("🎯 Meta", fmt_m(meta_g))
        with c2: st.metric("✅ Faturado", fmt_m(fat_g))
        with c3: st.metric("📝 Digitado", fmt_m(dig_g))
        with c_dev: st.metric("🔄 Devoluções", f"-{fmt_m(dev_g)}")
        with c_total: st.metric("💰 Total Líquido", fmt_m(total_liq_g))
        with c4: st.metric("🚩 Gap Real", fmt_m(falta_g))
        with c5: st.metric("🔥 Atingimento", f"{perc_g:.1f}%", delta=f"{gap_g:.1f}% vs Ideal")

        val_id_reais = (percentual_esperado / 100) * meta_g
        st.markdown(f"""> **Análise de ciclo:**
> * Devoluções acumuladas: **-{fmt_br(dev_g)}**.
> * Prazo final de faturamento: **{data_limite_faturamento.strftime('%d/%m')}**.
> * Dias úteis restantes (contando com a data selecionada): **{dias_uteis_restantes}**.
> * O atingimento ideal para hoje é de **{percentual_esperado:.1f}%** (equivale a **{fmt_br(val_id_reais)}**).""")

# ==========================================
# 📈 PERFORMANCE POR VENDEDOR (RANKING)
# ==========================================
st.markdown("---")
st.subheader(f"👥 Ranking Individual - {data_selecionada.strftime('%B').capitalize()}")

if df_vendedores_hist is not None:
    dados_v = df_vendedores_hist[df_vendedores_hist['Data'] == data_selecionada].copy()
    
    if not dados_v.empty:
        # Cálculos de Negócio
        dados_v['total_v'] = (dados_v['Faturado_Acumulado'] + dados_v['Digitado_Acumulado']) - dados_v['Devolucoes'].abs()
        dados_v['ating_v'] = (dados_v['total_v'] / dados_v['Meta'] * 100).fillna(0)
        dados_v['val_id_v'] = (percentual_esperado / 100) * dados_v['Meta']
        dados_v['diff_v'] = dados_v['total_v'] - dados_v['val_id_v']
        
        # Ticket Médio (Tratando divisão por zero)
        total_peds = dados_v['Fat_Ped'] + dados_v['Dig_Ped']
        dados_v['tm_v'] = (dados_v['total_v'] / total_peds).replace([float('inf'), -float('inf')], 0).fillna(0)
        
        # Ritmo
        dados_v['ritmo_v'] = ((dados_v['Meta'] - dados_v['total_v']).clip(lower=0) / dias_uteis_restantes).fillna(0)
        
        v_lista = dados_v.sort_values(by="ating_v", ascending=False).to_dict('records')
        
        # Início da Tabela HTML
        html_tabela = """
        <style>
            .tab-performance { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-top: 10px; }
            .tab-performance th { background-color: #f0f2f6; padding: 12px; text-align: center; color: #31333F; border-bottom: 2px solid #ccc; }
            .tab-performance td { padding: 12px; text-align: center; border-bottom: 1px solid #eee; }
            .prog-bg { background-color: #ddd; border-radius: 10px; width: 60px; height: 8px; display: inline-block; margin-right: 5px; }
            .prog-bar { background-color: #29b5e8; height: 8px; border-radius: 10px; }
            .val-sub { font-size: 11px; color: #757575; display: block; margin-top: 2px; }
            .col-vendedor { width: 220px !important; text-align: left !important; white-space: nowrap !important; }
        </style>
        <table class='tab-performance'>
            <thead>
                <tr>
                    <th>Pos.</th>
                    <th class='col-vendedor'>Vendedor</th>
                    <th>Meta</th>
                    <th>Faturado</th>
                    <th>Digitado</th>
                    <th>Devoluções</th>
                    <th>Total Líq (TM)</th>
                    <th>Atingimento</th>
                    <th>Ideal Hoje (R$)</th>
                    <th>Ritmo Diário</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, v in enumerate(v_lista):
            cor_ating = "#2E7D32" if v["ating_v"] >= percentual_esperado else "#C62828"
            cor_gap = "#2E7D32" if v["diff_v"] >= 0 else "#C62828"
            txt_gap = "Acima" if v["diff_v"] >= 0 else "Gap"
            
            html_tabela += f"""
                <tr>
                    <td>{i+1}º</td>
                    <td class='col-vendedor'><b>{v['Vendedor']}</b></td>
                    <td>{fmt_br(v['Meta'])}</td>
                    <td style='color: #2E7D32;'>{fmt_br(v['Faturado_Acumulado'])}<span class='val-sub'>{int(v['Fat_Ped'])} ped.</span></td>
                    <td style='color: #1565C0;'>{fmt_br(v['Digitado_Acumulado'])}<span class='val-sub'>{int(v['Dig_Ped'])} ped.</span></td>
                    <td style='color: #C62828;'>-{fmt_br(abs(v['Devolucoes']))}</td>
                    <td><b>{fmt_br(v['total_v'])}</b><span class='val-sub'>TM: {fmt_br(v['tm_v'])}</span></td>
                    <td>
                        <div class='prog-bg'><div class='prog-bar' style='width: {min(v['ating_v'], 100)}%'></div></div>
                        <span style='color: {cor_ating}; font-weight: bold;'>{v['ating_v']:.1f}%</span>
                    </td>
                    <td><b>{fmt_br(v['val_id_v'])}</b><span class='val-sub' style='color: {cor_gap}; font-weight: bold;'>{txt_gap}: {fmt_br(abs(v['diff_v']))}</span></td>
                    <td><span style='color: #E64A19; font-weight: bold;'>{fmt_br(v['ritmo_v'])}</span><span class='val-sub'>p/ dia</span></td>
                </tr>
            """
        
        html_tabela += "</tbody></table>"
        st.markdown(html_tabela, unsafe_allow_html=True)

# CSS para esconder ícones do Streamlit
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none !important; }</style>", unsafe_allow_html=True)
