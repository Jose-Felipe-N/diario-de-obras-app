import copy
import json
from pathlib import Path

import streamlit as st
import requests
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px

from config import API_URL
from confirmacoes import nome_confere, resumo_exclusao_diario, resumo_exclusao_obra
from formatos import data_br, data_com_semana, mes_br
from cronograma import carregar_etapas_comuns, montar_etapas, problema_nos_pesos
from opcoes_tela import adicionar_opcao, opcoes_com, remover_opcao, ultimo_diario_antes
from tela_analista import PERGUNTAS_DE_EXEMPLO, descrever_fontes

st.set_page_config(page_title="Diário de Obras", layout="wide", initial_sidebar_state="expanded")

URL_OBRAS = f"{API_URL}/obras/"
CAMINHO_CATALOGO = Path(__file__).parent / "dados" / "catalogo.json"


@st.cache_data
def carregar_catalogo():
    """Catálogo único de funções, equipamentos e gastos (o mesmo usado nos dados de avaliação)."""
    with open(CAMINHO_CATALOGO, encoding="utf-8") as f:
        return json.load(f)


# Valores padrão das listas. As edições feitas em Configurações ficam só na
# sessão e se perdem quando o app reinicia.
catalogo = carregar_catalogo()
listas_padrao = {
    "cat_efetivo": catalogo["funcoes"],
    "cat_equip_tipo": catalogo["tipos_equipamento"],
    "cat_gastos_categorias": catalogo["categorias_gasto"],
    "dict_equipamentos": catalogo["equipamentos"],
    "dict_gastos": catalogo["itens_gasto"],
}
for chave, padrao in listas_padrao.items():
    if chave not in st.session_state:
        st.session_state[chave] = copy.deepcopy(padrao)

CLIMA_ICONE = {
    "Sol": "☀️",
    "Nublado": "☁️",
    "Chuva": "🌧️",
    "Tempestade": "⛈️",
}

# A API grava os valores curtos (chaves); a tela mostra os rótulos.
ROTULO_AMBIENTE = {
    "Aberto": "Aberto (Sujeito ao clima)",
    "Fechado": "Fechado (Coberto)",
    "Misto": "Misto (Aberto e Fechado)",
}
ROTULO_LOCAL = {
    "Interior": "Interior (Coberto)",
    "Exterior": "Exterior (Céu Aberto)",
}


OPCOES_QUANTIDADE = list(range(1, 21))
OPCOES_HORAS = [h / 2 for h in range(2, 25)]  # 1 h a 12 h, de meia em meia hora
OPCOES_QUANTIDADE_EQUIP = list(range(1, 11))


def horas_fmt(horas):
    """8.0 -> '8 h'; 1.5 -> '1,5 h'."""
    return f"{horas:g} h".replace(".", ",")


def reais(valor):
    """Formata no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

import streamlit.components.v1 as components

def scroll_to_diario():
    """Injeta JS que rola a tela suavemente até o expander aberto."""
    components.html("""
        <script>
            setTimeout(() => {
                // Busca todos os expansores que estão abertos na tela
                const abertos = window.parent.document.querySelectorAll('details[open]');
                if (abertos.length > 0) {
                    // Rola suavemente para o último que foi aberto
                    abertos[abertos.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 250);
        </script>
    """, height=0)

def _excluir(url, aviso):
    """Chama o DELETE da API; se der certo, guarda o aviso para mostrar depois do recarregamento."""
    try:
        resposta = requests.delete(url)
    except requests.RequestException:
        st.error("Sem conexão com o servidor. Nada foi excluído.")
        return
    if resposta.status_code == 200:
        st.session_state["aviso_painel"] = aviso
        st.rerun()
    else:
        st.error(f"A exclusão falhou (erro {resposta.status_code}). Nada foi excluído.")


@st.dialog("Excluir obra")
def confirmar_exclusao_obra(obra):
    st.warning(resumo_exclusao_obra(obra))
    digitado = st.text_input(f"Para confirmar, digite o nome da obra ({obra['nome']}) e tecle Enter:")
    col_cancelar, col_excluir = st.columns(2)
    if col_cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if col_excluir.button("Excluir obra", type="primary", width="stretch",
                          disabled=not nome_confere(digitado, obra["nome"])):
        _excluir(f"{API_URL}/obras/{obra['id']}", f"Obra '{obra['nome']}' excluída.")


@st.dialog("Excluir diário")
def confirmar_exclusao_diario(diario, obra_nome):
    st.warning(resumo_exclusao_diario(diario, obra_nome))
    col_cancelar, col_excluir = st.columns(2)
    if col_cancelar.button("Cancelar", width="stretch"):
        st.rerun()
    if col_excluir.button("Excluir diário", type="primary", width="stretch"):
        _excluir(f"{API_URL}/diarios/{diario['id']}", f"Diário de {data_br(diario['data'])} excluído.")


def mini_card(label, value, detalhe="", cor="#005C99"):
    """Card compacto em HTML — bem menor que st.metric."""
    detalhe_html = f'<div style="font-size:11px;color:#999;margin-top:2px;">{detalhe}</div>' if detalhe else ""
    st.markdown(f"""
        <div style="
            padding: 7px 10px;
            margin-bottom: 7px;
            border-left: 3px solid {cor};
            background: rgba(255,255,255,0.04);
            border-radius: 5px;
        ">
            <div style="font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:0.4px;">{label}</div>
            <div style="font-size:15px;font-weight:700;color:#eee;">{value}</div>
            {detalhe_html}
        </div>
    """, unsafe_allow_html=True)

PAGINAS = ["Início", "Painel de Obras", "Orçamentos", "Nova Obra", "Novo Diário", "Analista IA", "Configurações"]

with st.sidebar:
    st.title("🏗️ Gestão de Obras")
    st.write("Navegue pelas ferramentas:")
    # O menu devolve a opção clicada ou, se não houve clique, a opção padrão. Por isso a padrão
    # acompanha a página atual: senão, qualquer interação depois de uma navegação feita pelo código
    # (ex.: Início -> "Preencher" -> Novo Diário) voltaria para o Início. Uma navegação pelo código
    # ("ir_para") troca a chave do menu, que recomeça já na página de destino.
    ir_para = st.session_state.pop("ir_para", None)
    if ir_para:
        st.session_state["pagina"] = ir_para
        st.session_state["menu_versao"] = st.session_state.get("menu_versao", 0) + 1
    pagina_atual = st.session_state.get("pagina", PAGINAS[0])
    menu_selecionado = option_menu(
        menu_title=None,
        options=PAGINAS,
        default_index=PAGINAS.index(pagina_atual),
        key=f"menu_principal_{st.session_state.get('menu_versao', 0)}",
        icons=["house-fill", "bar-chart-fill", "calculator-fill", "building-fill-add", "journal-text", "robot", "gear-fill"],
        menu_icon="cast",
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "18px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#333333"},
            "nav-link-selected": {"background-color": "#005C99"},
        }
    )
    st.session_state["pagina"] = menu_selecionado
    st.divider()
    st.caption("Sistema de Gestão v1.0")

# ── INÍCIO ─────────────────────────────────────────────────────────────────────

if menu_selecionado == "Início":
    st.title("🏠 Início")
    st.write("Bem-vindo ao Centro de Comando de sua construtora.")
    st.divider()
    try:
        resposta = requests.get(f"{API_URL}/dashboard/")
        if resposta.status_code == 200:
            dados_dash = resposta.json()
            st.subheader("📊 Resumo de Hoje")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric(label="🏗️ Obras em Andamento", value=dados_dash["obras_ativas"])
            with col_m2:
                st.metric(label="👷 Efetivo Total Hoje", value=dados_dash["efetivo_hoje"])
            with col_m3:
                valor_formatado = f"R$ {dados_dash['gastos_hoje']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                st.metric(label="💰 Gastos do Dia", value=valor_formatado)
            st.divider()
            col_alertas, col_acoes = st.columns([2, 1], gap="large")
            with col_alertas:
                st.subheader("⚠️ Alertas e Status")
                tem_alerta = False
                for clima in dados_dash["alertas_clima"]:
                    st.warning(f"**{clima['obra']}:** Condições climáticas adversas ({clima['clima']}).")
                    tem_alerta = True
                for pausada in dados_dash["alertas_pausadas"]:
                    st.error(f"**{pausada['obra']}:** A obra encontra-se com o status 'Pausada'.")
                    tem_alerta = True
                for diario in dados_dash["diarios_preenchidos"]:
                    st.success(f"**{diario['obra']}:** Diário de obra preenchido com sucesso hoje.")
                    tem_alerta = True
                if not tem_alerta:
                    st.info("Nenhum alerta crítico ou diário preenchido no dia de hoje.")
            with col_acoes:
                st.subheader("📝 Diários pendentes hoje")
                pendentes = dados_dash.get("obras_sem_diario_hoje", [])
                if not pendentes:
                    st.success("Todas as obras em andamento já têm o diário de hoje.")
                for pendente in pendentes:
                    col_nome, col_ir = st.columns([3, 2], vertical_alignment="center")
                    col_nome.markdown(f"**{pendente['obra']}**")
                    if col_ir.button("Preencher", key=f"preencher_{pendente['id']}", width="stretch"):
                        st.session_state["nd_obra"] = pendente["obra"]
                        st.session_state["ir_para"] = "Novo Diário"
                        st.rerun()
        else:
            st.error("Erro ao carregar os dados do painel.")
    except Exception as e:
        st.error(f"Erro de conexão com o servidor: {e}")

# ── PAINEL DE OBRAS ────────────────────────────────────────────────────────────

elif menu_selecionado == "Painel de Obras":
    st.title("📊 Painel de Obras")
    st.write("Visão geral dos relatórios e andamento do canteiro.")
    aviso = st.session_state.pop("aviso_painel", None)
    if aviso:
        st.success(aviso)

    try:
        resposta = requests.get(URL_OBRAS)
        if resposta.status_code == 200:
            dados = resposta.json()
            st.divider()

            nomes_obras = [obra['nome'] for obra in dados]
            obra_selecionada = st.selectbox("🔍 Obra", nomes_obras, index=None, key="busca_obra",
                                            placeholder="Escolha uma obra para ver os diários…")

            if obra_selecionada:
                obras_filtradas = [obra for obra in dados if obra['nome'] == obra_selecionada]

                for obra in obras_filtradas:
                    col_tit, col_del = st.columns([5, 1])
                    with col_tit:
                        st.subheader(f"🏢 Obra: {obra['nome']}")
                    with col_del:
                        if st.button("🗑️ Excluir Obra", key=f"del_obra_{obra['id']}"):
                            confirmar_exclusao_obra(obra)

                    st.write(f"**Endereço:** {obra['endereco']}")
                    st.write(f"**Ambiente:** {ROTULO_AMBIENTE.get(obra.get('ambiente'), 'Não informado')}")

                    col_status, col_btn = st.columns([3, 1])
                    with col_status:
                        lista_status = ["Planejamento", "Em andamento", "Pausada", "Concluída"]
                        index_atual = lista_status.index(obra['status']) if obra['status'] in lista_status else 0
                        novo_status = st.selectbox("Status Atual:", lista_status, index=index_atual, key=f"sel_status_{obra['id']}")
                    with col_btn:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Atualizar Status", key=f"btn_status_{obra['id']}"):
                            resp_put = requests.put(
                                f"{API_URL}/obras/{obra['id']}/status",
                                json={"status": novo_status}
                            )
                            if resp_put.status_code == 200:
                                st.success("Status atualizado!")
                                st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)

                    try:
                        res_progresso = requests.get(f"{API_URL}/obras/{obra['id']}/progresso")
                        valor_progresso = res_progresso.json().get("progresso", 0.0) if res_progresso.status_code == 200 else 0.0
                    except:
                        valor_progresso = 0.0

                    valor_barra = int(valor_progresso)
                    if valor_barra > 100: 
                        valor_barra = 100 

                    st.markdown("### 📈 Andamento do Projeto")
                    st.progress(valor_barra, text=f"Progresso Físico Realizado: {valor_progresso:.1f}%")
                    st.divider()

                    if not obra['diarios']:
                        st.info("Nenhum diário registrado para esta obra.")
                        

                    if "diario_aberto" not in st.session_state:
                        st.session_state["diario_aberto"] = None

                    diarios_obra = sorted(obra['diarios'], key=lambda d: (d['data'], d['id']), reverse=True)
                    meses = list(dict.fromkeys(d['data'][:7] for d in diarios_obra))
                    if len(meses) > 1:
                        mes = st.selectbox("📅 Mês", ["todos"] + meses, index=1, key=f"mes_{obra['id']}",
                                           format_func=lambda m: "Todos os meses" if m == "todos" else mes_br(m).capitalize())
                        if mes != "todos":
                            diarios_obra = [d for d in diarios_obra if d['data'].startswith(mes)]

                    for diario in diarios_obra:
                        clima_m = diario.get('clima_manha', 'Sol')
                        clima_t = diario.get('clima_tarde', 'Sol')
                        icone_m = CLIMA_ICONE.get(clima_m, "🌤️")
                        icone_t = CLIMA_ICONE.get(clima_t, "🌤️")

                        total_trabalhadores = sum(e['quantidade'] for e in diario.get('efetivos', []))
                        total_gastos = sum(g['valor'] for g in diario.get('gastos', []))
                        total_gastos_fmt = f"R$ {total_gastos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                        label_expander = (
                            f"📅  {data_com_semana(diario['data'])}   |   "
                            f"Manhã: {icone_m} {clima_m}   "
                            f"Tarde: {icone_t} {clima_t}   |   "
                            f"👷 {total_trabalhadores} trab.   |   "
                            f"💰 {total_gastos_fmt}"
                        )

                        aberto = st.expander(label_expander)
                        with aberto:
                            scroll_to_diario()

                            with st.container(border=True):
                                st.markdown("##### ✏️ Editar Diário")
                                col_c1, col_c2 = st.columns(2)
                                with col_c1:
                                    edit_m = st.selectbox(
                                        "☀️ Clima Manhã",
                                        ["Sol", "Chuva", "Nublado", "Tempestade"],
                                        index=["Sol", "Chuva", "Nublado", "Tempestade"].index(clima_m),
                                        key=f"ed_m_{diario['id']}"
                                    )
                                with col_c2:
                                    edit_t = st.selectbox(
                                        "🌙 Clima Tarde",
                                        ["Sol", "Chuva", "Nublado", "Tempestade"],
                                        index=["Sol", "Chuva", "Nublado", "Tempestade"].index(clima_t),
                                        key=f"ed_t_{diario['id']}"
                                    )
                                edit_obs = st.text_area(
                                    "📋 Observações",
                                    diario.get('observacoes_gerais') or "",
                                    placeholder="Nenhuma observação registrada.",
                                    key=f"ed_obs_{diario['id']}",
                                    height=80
                                )
                                col_e1, col_e2 = st.columns(2)
                                with col_e1:
                                    if st.button("💾 Salvar", key=f"save_ed_{diario['id']}", width="stretch"):
                                        requests.put(
                                            f"{API_URL}/diarios/{diario['id']}",
                                            json={"clima_manha": edit_m, "clima_tarde": edit_t, "observacoes_gerais": edit_obs}
                                        )
                                        st.success("Diário atualizado!")
                                        st.rerun()
                                with col_e2:
                                    if st.button("🗑️ Excluir", key=f"del_dia_{diario['id']}", width="stretch", type="primary"):
                                        confirmar_exclusao_diario(diario, obra['nome'])


                            col_trab, col_equip, col_gastos = st.columns(3)

                            ALTURA_CAIXA = 320 

                            with col_trab:
                                with st.container(border=True, height=ALTURA_CAIXA):
                                    st.markdown("**👷 Trabalhadores**")
                                    efetivos = diario.get('efetivos', [])
                                    if efetivos:
                                        for ef in efetivos:
                                            mini_card(ef['funcao'], f"{ef['quantidade']} pessoa(s)", f"{ef['horas_trabalhadas']}h trabalhadas", "#005C99")
                                    else:
                                        st.caption("Nenhum registrado.")

                            with col_equip:
                                with st.container(border=True, height=ALTURA_CAIXA):
                                    st.markdown("**🚜 Equipamentos**")
                                    equipamentos = diario.get('equipamentos', [])
                                    if equipamentos:
                                        for eq in equipamentos:
                                            mini_card(eq['nome_item'], f"{eq['quantidade']} un.", eq.get('tipo', ''), "#2e7d32")
                                    else:
                                        st.caption("Nenhum registrado.")

                            with col_gastos:
                                with st.container(border=True, height=ALTURA_CAIXA):
                                    st.markdown("**💰 Gastos**")
                                    gastos = diario.get('gastos', [])
                                    if gastos:
                                        for g in gastos:
                                            valor_fmt = f"R$ {g['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                            mini_card(g['item'], valor_fmt, g.get('categoria', ''), "#b45309")
                                            
                                        st.markdown(f"""
                                            <div style="margin-top:15px;margin-bottom:10px;padding:10px 15px;background:rgba(255,255,255,0.07);border-radius:5px;text-align:right;">
                                                <span style="font-size:11px;color:#aaa;">TOTAL DO DIA</span><br>
                                                <span style="font-size:16px;font-weight:700;color:#eee;">{total_gastos_fmt}</span>
                                            </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.caption("Nenhum registrado.")

                    st.divider()
        else:
            st.error("Erro ao buscar dados.")
    except Exception as e:
        st.error(f"Erro: {e}")

# ── NOVA OBRA ──────────────────────────────────────────────────────────────────

elif menu_selecionado == "Nova Obra":
    st.title("➕ Cadastrar Nova Obra")
    st.write("Preencha os dados abaixo para iniciar um novo projeto.")
    aviso = st.session_state.pop("aviso_nova_obra", None)
    if aviso:
        st.success(aviso)

    # Sem st.form: a escolha de etapas precisa remontar a tabela na hora. O número muda a cada
    # obra salva e entra nas chaves dos campos, que assim só são limpos quando o salvamento dá certo.
    n_form = st.session_state.setdefault("form_nova_obra_n", 0)

    with st.container(border=True):
        input_nome = st.text_input("Nome da Obra", key=f"nome_obra_{n_form}")
        input_endereco = st.text_input("Endereço Completo", key=f"endereco_obra_{n_form}")

        col1, col2 = st.columns(2)
        with col1:
            input_data = st.date_input("Data de Início", key=f"data_obra_{n_form}")
        with col2:
            input_status = st.selectbox("Status Atual", ["Planejamento", "Em andamento", "Pausada", "Concluída"],
                                        key=f"status_obra_{n_form}")

        st.markdown("**Condições do Local:**")
        input_ambiente = st.radio(
            "Selecione o tipo de ambiente da obra:",
            list(ROTULO_AMBIENTE),
            format_func=ROTULO_AMBIENTE.get,
            horizontal=True,
            key=f"ambiente_obra_{n_form}",
        )

        st.markdown("---")
        st.markdown("### 🗓️ Cronograma (opcional)")
        escolhidas = st.multiselect(
            "Quais etapas fazem parte deste contrato?",
            [e["nome"] for e in carregar_etapas_comuns()],
            key=f"etapas_contrato_{n_form}",
            placeholder="Escolha as etapas; a tabela abaixo é montada com elas",
            help="Os pesos de referência são redistribuídos entre as etapas escolhidas para somar 100%.",
        )
        st.caption("Escolha as etapas primeiro e depois ajuste nomes, pesos e dias na tabela: mudar a escolha "
                   "remonta a tabela. Use o '+' no canto da tabela para incluir uma etapa que não está na lista.")

        df_etapas = pd.DataFrame(montar_etapas(escolhidas, carregar_etapas_comuns()),
                                 columns=["Nome da Etapa", "Peso (%)", "Dias Estimados"])

        etapas_preenchidas = st.data_editor(
            df_etapas,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            # A tabela é remontada quando a escolha de etapas muda.
            key=f"cadastro_etapas_obra_{n_form}_{'|'.join(escolhidas)}",
            column_config={
                "Nome da Etapa": st.column_config.TextColumn("Nome da Etapa"),
                "Peso (%)": st.column_config.NumberColumn("Peso (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"),
                "Dias Estimados": st.column_config.NumberColumn("Dias Estimados", min_value=0, step=1),
            },
        )

        etapas_lista = []
        if etapas_preenchidas is not None and not etapas_preenchidas.empty:
            for index, row in etapas_preenchidas.iterrows():
                # Evita processar linhas totalmente vazias ou sem nome
                if pd.notna(row["Nome da Etapa"]) and str(row["Nome da Etapa"]).strip() != "":
                    etapas_lista.append({
                        "nome_etapa": str(row["Nome da Etapa"]),
                        "peso_percentual": float(row["Peso (%)"]) if pd.notna(row["Peso (%)"]) else 0.0,
                        "dias_estimados": int(row["Dias Estimados"]) if pd.notna(row["Dias Estimados"]) else 0
                    })

        problema = problema_nos_pesos(etapas_lista)
        if etapas_lista:
            soma = sum(e["peso_percentual"] for e in etapas_lista)
            if problema:
                st.warning(f"Soma dos pesos: {soma:g}%".replace(".", ",") + " — precisa ser 100% para salvar.")
            else:
                st.caption(f"✅ Soma dos pesos: {soma:g}%".replace(".", ","))

        if st.button("💾 Salvar Obra", key=f"salvar_obra_{n_form}"):
            if problema:
                st.error(problema)
                st.stop()

            pacote_dados = {
                "nome": input_nome,
                "endereco": input_endereco,
                "data_inicio": str(input_data),
                "status": input_status,
                "ambiente": input_ambiente,
                "etapas": etapas_lista
            }

            try:
                resposta_post = requests.post(URL_OBRAS, json=pacote_dados)
                if resposta_post.status_code == 200:
                    st.session_state["aviso_nova_obra"] = f"✨ A obra '{input_nome}' e seu cronograma foram criados com sucesso!"
                    st.session_state["form_nova_obra_n"] = n_form + 1
                    st.rerun()
                else:
                    st.error("Erro ao tentar salvar a obra. Verifique as configurações do servidor.")
            except Exception as e:
                st.error("Erro de conexão com a API.")

# ── NOVO DIÁRIO ────────────────────────────────────────────────────────────────
elif menu_selecionado == "Novo Diário":
    st.title("📝 Preencher Diário de Obra")
    aviso = st.session_state.pop("aviso_novo_diario", None)
    if aviso:
        st.success(aviso)
    try:
        resp_obras = requests.get(URL_OBRAS)
        obras_disponiveis = resp_obras.json() if resp_obras.status_code == 200 else []
    except requests.RequestException:
        obras_disponiveis = []

    if not obras_disponiveis:
        st.warning("⚠️ Você precisa cadastrar pelo menos uma Obra antes de criar um Diário.")
    else:
        obras_por_nome = {o["nome"]: o for o in obras_disponiveis}
        escolha = st.selectbox("🏗️ Obra", list(obras_por_nome), index=None, key="nd_obra",
                               placeholder="Escolha a obra do diário…")

        if escolha:
            obra_selecionada = obras_por_nome[escolha]

            with st.expander("⚙️ Gerenciar Categorias Rápidas"):
                st.caption("As listas editadas aqui valem só até o app reiniciar.")
                col_add1, col_add2, col_add3 = st.columns(3)
                with col_add1:
                    st.markdown("**👷 Efetivo**")
                    nova_func = st.text_input("Nova Função", key="in_func")
                    if st.button("➕ Add", key="btn_add_func"):
                        if adicionar_opcao(st.session_state["cat_efetivo"], nova_func):
                            st.rerun()
                    func_remover = st.selectbox("Remover Função", st.session_state["cat_efetivo"], key="sel_rm_func")
                    if st.button("🗑️ Remover", key="btn_rm_func"):
                        if remover_opcao(st.session_state["cat_efetivo"], func_remover):
                            st.rerun()
                        else:
                            st.error("Mantenha pelo menos uma opção.")
                with col_add2:
                    st.markdown("**🚜 Equipamentos**")
                    novo_eq_nome = st.text_input("Novo Equipamento", key="in_eq_nome")
                    nova_eq_cat = st.selectbox("Categoria do Equip.", st.session_state["cat_equip_tipo"], key="in_eq_cat")

                    if st.button("➕ Add Equipamento", key="btn_add_eq_nome"):
                        if adicionar_opcao(st.session_state["dict_equipamentos"], novo_eq_nome, nova_eq_cat):
                            st.rerun()
                    equip_remover = st.selectbox("Remover Equipamento", list(st.session_state["dict_equipamentos"]), key="sel_rm_equip")
                    if st.button("🗑️ Remover Equipamento", key="btn_rm_equip"):
                        if remover_opcao(st.session_state["dict_equipamentos"], equip_remover):
                            st.rerun()
                        else:
                            st.error("Mantenha pelo menos uma opção.")

                with col_add3:
                    st.markdown("**💰 Gastos**")
                    novo_gasto_item = st.text_input("Novo Item de Gasto", key="in_gasto_item")
                    nova_gasto_cat = st.selectbox("Categoria do Gasto", st.session_state["cat_gastos_categorias"], key="in_gasto_cat")

                    if st.button("➕ Add Item", key="btn_add_gasto_item"):
                        if adicionar_opcao(st.session_state["dict_gastos"], novo_gasto_item, nova_gasto_cat):
                            st.rerun()
                    # Remove da mesma lista que alimenta a tabela de gastos do diário.
                    gasto_item_remover = st.selectbox("Remover Item", list(st.session_state["dict_gastos"]), key="sel_rm_gasto_item")
                    if st.button("🗑️ Remover Item", key="btn_rm_gasto_item"):
                        if remover_opcao(st.session_state["dict_gastos"], gasto_item_remover):
                            st.rerun()
                        else:
                            st.error("Mantenha pelo menos uma opção.")

            # Sem st.form: a data, o botão de copiar e o aviso de diário repetido precisam reagir na hora.
            # O número muda a cada diário salvo e entra nas chaves dos campos, que assim só são limpos
            # quando o salvamento dá certo (um erro de conexão não apaga o que foi digitado).
            n_d = st.session_state.setdefault("form_novo_diario_n", 0)
            sufixo = f"{n_d}_{obra_selecionada['id']}"
            diarios_da_obra = obra_selecionada.get("diarios") or []

            with st.container(border=True):
                data_diario = st.date_input("Data do Diário", key=f"nd_data_{sufixo}", format="DD/MM/YYYY")
                if any(d["data"] == data_diario.isoformat() for d in diarios_da_obra):
                    st.warning(f"Já existe um diário de {data_br(data_diario.isoformat())} para esta obra. Salvar cria um "
                               "segundo diário no mesmo dia; para corrigir o existente, use o Painel de Obras.")

                col_clima1, col_clima2 = st.columns(2)
                with col_clima1:
                    clima_manha = st.selectbox("Clima (Manhã)", ["Sol", "Chuva", "Nublado", "Tempestade"], key=f"nd_cm_{sufixo}")
                with col_clima2:
                    clima_tarde = st.selectbox("Clima (Tarde)", ["Sol", "Chuva", "Nublado", "Tempestade"], key=f"nd_ct_{sufixo}")

                ambiente_obra = obra_selecionada.get("ambiente")
                if ambiente_obra == "Misto":
                    st.markdown("### 📍 Localização do Trabalho")
                    local_dia = st.radio("Onde a maior parte do trabalho foi realizada hoje?", list(ROTULO_LOCAL),
                                         format_func=ROTULO_LOCAL.get, horizontal=True, key=f"nd_local_{sufixo}")
                elif ambiente_obra == "Fechado":
                    local_dia = "Interior"
                    st.info("ℹ️ Obra em ambiente fechado. Localização definida automaticamente como Interior.")
                else:
                    local_dia = "Exterior"
                    st.info("ℹ️ Obra em ambiente aberto. Localização definida automaticamente como Exterior.")

                observacoes = st.text_area(
                    "Observações Gerais", key=f"nd_obs_{sufixo}",
                    placeholder="Ex.: Choveu à tarde e a equipe passou para a área coberta. "
                                "Faltou energia por cerca de 4 horas; o gerador manteve a máquina de solda.",
                    help="Escreva o que aconteceu com números e duração claros ('por 4 horas', não 'umas 4 h'). "
                         "O Analista IA usa este texto para responder perguntas sobre a obra.",
                )

                # Copiar a equipe e os equipamentos do diário anterior: costumam repetir de um dia para o outro.
                anterior = ultimo_diario_antes(diarios_da_obra, data_diario.isoformat())
                chave_copia = f"nd_copia_{sufixo}"
                if anterior:
                    if st.button(f"📋 Copiar equipe e equipamentos do diário de {data_br(anterior['data'])}",
                                 key=f"nd_btn_copia_{sufixo}"):
                        st.session_state[chave_copia] = anterior
                copia = st.session_state.get(chave_copia)
                versao = copia["id"] if copia else "novo"

                st.markdown("### 👷 Trabalhadores (Efetivo)")
                # Listas em vez de digitação: mais rápido de preencher e evita a caixa de edição
                # numérica do Streamlit, que fica fora do lugar quando a página rola.
                # Horas a partir de 1 h para registrar dias parados (chuva forte costuma dar 2 h).
                linhas_trab = ([{k: e[k] for k in ("funcao", "quantidade", "horas_trabalhadas")} for e in copia["efetivos"]]
                               if copia and copia.get("efetivos")
                               else [{"funcao": st.session_state["cat_efetivo"][0], "quantidade": 1, "horas_trabalhadas": 8.0}])
                tabela_trabalhadores = st.data_editor(
                    linhas_trab, num_rows="dynamic", hide_index=True, key=f"ed_trab_{sufixo}_{versao}",
                    column_config={
                        "funcao": st.column_config.SelectboxColumn(
                            "Função", options=opcoes_com(st.session_state["cat_efetivo"], linhas_trab, "funcao"), required=True),
                        "quantidade": st.column_config.SelectboxColumn(
                            "Quantidade", options=opcoes_com(OPCOES_QUANTIDADE, linhas_trab, "quantidade"), default=1, required=True),
                        "horas_trabalhadas": st.column_config.SelectboxColumn(
                            "Horas Trabalhadas", options=opcoes_com(OPCOES_HORAS, linhas_trab, "horas_trabalhadas"),
                            default=8.0, required=True, format_func=horas_fmt),
                    }
                )

                st.markdown("### 🚜 Equipamentos")
                opcoes_equip = list(st.session_state["dict_equipamentos"].keys())
                linhas_equip = ([{k: e[k] for k in ("nome_item", "quantidade")} for e in copia["equipamentos"]]
                                if copia and copia.get("equipamentos") else [{"nome_item": opcoes_equip[0], "quantidade": 1}])
                tabela_equipamentos = st.data_editor(
                    linhas_equip, num_rows="dynamic", hide_index=True, key=f"ed_equip_{sufixo}_{versao}",
                    column_config={
                        "nome_item": st.column_config.SelectboxColumn(
                            "Equipamento", options=opcoes_com(opcoes_equip, linhas_equip, "nome_item"), required=True),
                        "quantidade": st.column_config.SelectboxColumn(
                            "Quantidade", options=opcoes_com(OPCOES_QUANTIDADE_EQUIP, linhas_equip, "quantidade"),
                            default=1, required=True),
                    }
                )
                tipos_copiados = {e["nome_item"]: e.get("tipo") for e in (copia or {}).get("equipamentos", [])}

                st.markdown("### 💰 Controle Financeiro (Gastos do Dia)")
                opcoes_gastos = list(st.session_state["dict_gastos"].keys())
                tabela_gastos = st.data_editor(
                    [{"item": opcoes_gastos[0], "valor": 0}],
                    num_rows="dynamic", hide_index=True, key=f"ed_gastos_{sufixo}",
                    column_config={
                        "item": st.column_config.SelectboxColumn("Descrição", options=opcoes_gastos, required=True),
                        "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0.0, step=0.01, format="R$ %.2f", required=True),
                    }
                )

                if st.button("📝 Salvar Diário", key=f"nd_salvar_{sufixo}", type="primary"):
                    pacote_diario = {
                        "data": data_diario.isoformat(), "clima_manha": clima_manha, "clima_tarde": clima_tarde,
                        "observacoes_gerais": observacoes, "local_dia": local_dia, "obra_id": obra_selecionada["id"],
                        "efetivos": [t for t in tabela_trabalhadores if t.get("funcao") and t.get("quantidade")],
                        "equipamentos": [
                            {"nome_item": e["nome_item"], "quantidade": e["quantidade"],
                             "tipo": st.session_state["dict_equipamentos"].get(e["nome_item"]) or tipos_copiados.get(e["nome_item"]) or "Outros"}
                            for e in tabela_equipamentos if e.get("nome_item") and e.get("quantidade")],
                        "gastos": [
                            {"item": g["item"], "valor": g["valor"],
                             "categoria": st.session_state["dict_gastos"].get(g["item"], "Outros")}
                            for g in tabela_gastos if g.get("item") and (g.get("valor") or 0) > 0],
                    }
                    try:
                        resposta_diario = requests.post(f"{API_URL}/diarios/completo", json=pacote_diario)
                    except requests.RequestException:
                        st.error("Sem conexão com o servidor. O diário não foi salvo; os dados digitados continuam aqui.")
                    else:
                        if resposta_diario.status_code == 200:
                            st.session_state["aviso_novo_diario"] = (
                                f"✨ Diário de {data_br(pacote_diario['data'])} registrado para {obra_selecionada['nome']}!")
                            st.session_state["form_novo_diario_n"] = n_d + 1
                            st.rerun()
                        else:
                            st.error(f"O diário não foi salvo (erro {resposta_diario.status_code}); "
                                     "os dados digitados continuam aqui. Confira os campos e tente de novo.")

# ── ANALISTA IA ────────────────────────────────────────────────────────────────
elif menu_selecionado == "Analista IA":
    st.markdown("## 🧠 Analista IA")
    st.markdown("Converse com o sistema sobre o andamento das obras, gastos e uso de equipamentos.")

    try:
        res_obras = requests.get(f"{API_URL}/ia/obras_disponiveis")
        lista_obras = res_obras.json() if res_obras.status_code == 200 else []
    except requests.RequestException:
        lista_obras = []

    opcoes_obras = {"🌍 Visão Geral (Todas as Obras)": None}
    for o in lista_obras:
        opcoes_obras[f"🏗️ {o['nome']}"] = o["id"]

    st.markdown("### 🎯 Foco da Análise")
    col_foco, col_nova = st.columns([4, 1], vertical_alignment="bottom")
    with col_foco:
        obra_selecionada_nome = st.selectbox("Escolha a obra para a IA focar:", list(opcoes_obras.keys()))
    obra_selecionada_id = opcoes_obras[obra_selecionada_nome]

    # Cada conversa é sobre um foco: trocar de obra começa uma conversa nova, para o histórico
    # de uma obra não ser enviado junto com perguntas sobre outra.
    if st.session_state.get("chat_obra_id", "inicio") != obra_selecionada_id:
        st.session_state["mensagens_chat"] = []
        st.session_state["chat_obra_id"] = obra_selecionada_id
    with col_nova:
        if st.button("🧹 Nova conversa", width="stretch",
                     disabled=not st.session_state.get("mensagens_chat")):
            st.session_state["mensagens_chat"] = []
            st.rerun()

    st.divider()

    if "mensagens_chat" not in st.session_state:
        st.session_state["mensagens_chat"] = []

    def mostrar_grafico(grafico, chave):
        st.markdown(f"**📊 {grafico.get('titulo') or 'Gráfico Analítico'}**")
        df_grafico = pd.DataFrame(list(grafico["dados"].items()), columns=["Categoria", "Valor"])
        try:
            df_grafico["Categoria_Data"] = pd.to_datetime(df_grafico["Categoria"], format="%d/%m/%Y")
            df_grafico = df_grafico.sort_values(by="Categoria_Data").drop(columns=["Categoria_Data"])
        except Exception:
            pass
        tipo = (grafico.get("tipo") or "barras").lower()
        if tipo == "pizza":
            fig = px.pie(df_grafico, values="Valor", names="Categoria", hole=0.3)
        elif tipo == "linha":
            fig = px.line(df_grafico, x="Categoria", y="Valor", markers=True)
        else:  # padrão: barras
            fig = px.bar(df_grafico, x="Categoria", y="Valor")
        st.plotly_chart(fig, width="stretch", key=chave)

    def mostrar_resposta(indice, msg):
        """Texto, gráfico, fontes consultadas e avaliação 👍/👎 de uma resposta do assistente."""
        st.markdown(msg["content"])
        if msg.get("grafico"):
            mostrar_grafico(msg["grafico"], chave=f"grafico_{st.session_state['chat_obra_id']}_{indice}")
        fontes = msg.get("fontes") or []
        with st.expander("🔎 Como cheguei a essa resposta"):
            if fontes:
                st.markdown("Consultei no sistema:\n" + "\n".join(f"- {f}" for f in fontes))
            else:
                st.markdown("Respondi sem consultar os dados das obras.")
        nota = st.feedback("thumbs", key=f"feedback_{st.session_state['chat_obra_id']}_{indice}")
        if nota is not None and not msg.get("nota_enviada"):
            try:
                requests.post(f"{API_URL}/ia/feedback", json={
                    "pergunta": msg.get("pergunta", ""), "resposta": msg["content"],
                    "nota": "positivo" if nota == 1 else "negativo",
                    "obra_id": st.session_state["chat_obra_id"], "ferramentas": msg.get("ferramentas", []),
                })
                msg["nota_enviada"] = True
                st.toast("Obrigado! Sua avaliação ajuda a melhorar o assistente.")
            except requests.RequestException:
                st.toast("Não consegui registrar a avaliação agora.")

    for i, msg in enumerate(st.session_state["mensagens_chat"]):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                mostrar_resposta(i, msg)
            else:
                st.markdown(msg["content"])

    pergunta = st.chat_input("Pergunte sobre as obras, por exemplo: qual obra está atrasada?")

    if not st.session_state["mensagens_chat"] and not pergunta:
        st.caption("Sugestões para começar:")
        exemplos = PERGUNTAS_DE_EXEMPLO["obra" if obra_selecionada_id else None]
        for coluna, exemplo in zip(st.columns(len(exemplos)), exemplos):
            if coluna.button(exemplo, key=f"exemplo_{exemplo}", width="stretch"):
                pergunta = exemplo

    if pergunta:
        historico_envio = [{"role": m["role"], "content": m["content"]} for m in st.session_state["mensagens_chat"]]
        st.session_state["mensagens_chat"].append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Consultando os dados das obras… pode levar até 1 minuto."):
                try:
                    resposta_api = requests.post(
                        f"{API_URL}/ia/chat",
                        json={"mensagem": pergunta, "historico": historico_envio, "obra_id": obra_selecionada_id},
                    )
                except requests.RequestException:
                    resposta_api = None
                    st.error("Sem conexão com o servidor. Confira se a API está no ar e tente de novo.")

            if resposta_api is not None and resposta_api.status_code == 200:
                dados_resposta = resposta_api.json()
                uso = dados_resposta.get("uso") or {}
                grafico = None
                if dados_resposta.get("gerar_grafico") and dados_resposta.get("dados_grafico"):
                    grafico = {"titulo": dados_resposta.get("titulo_grafico"), "tipo": dados_resposta.get("tipo_grafico"),
                               "dados": dados_resposta["dados_grafico"]}
                nova = {"role": "assistant", "content": dados_resposta.get("resposta", "Erro ao ler a mensagem."),
                        "grafico": grafico, "fontes": descrever_fontes(uso), "ferramentas": uso.get("ferramentas", []),
                        "pergunta": pergunta}
                st.session_state["mensagens_chat"].append(nova)
                mostrar_resposta(len(st.session_state["mensagens_chat"]) - 1, nova)
            elif resposta_api is not None:
                # A API devolve uma mensagem amigável (cota esgotada, modelo sobrecarregado etc.).
                try:
                    mensagem_erro = resposta_api.json().get("resposta")
                except ValueError:
                    mensagem_erro = None
                st.warning(mensagem_erro or "O Analista IA não conseguiu responder agora. Tente de novo.")

# ── CONFIGURAÇÕES ──────────────────────────────────────────────────────────────

elif menu_selecionado == "Configurações":
    st.title("⚙️ Configurações do Sistema")
    st.write("Gerencie as categorias padrão que aparecem nos formulários.")

    sub_efetivo, sub_equip_nomes, sub_equip_tipo, sub_gastos_itens, sub_gastos_cat = st.tabs([
        "👷 Efetivos (Funções)", "🚜 Equipamentos (Nomes)", "🔧 Equipamentos (Tipos)", "💰 Gastos (Itens)", "📂 Gastos (Categorias)",
    ])

    # FUNÇÃO 1: Para listas simples (Usada no Efetivo)
    def render_config_tab(session_key, label_tabela, label_add, label_rm, key_prefix):
        col_tabela, col_acoes = st.columns([1, 1], gap="large")
        with col_tabela:
            st.subheader(label_tabela)
            st.dataframe({"Itens": st.session_state[session_key]}, hide_index=True, width="stretch")
        with col_acoes:
            with st.container(border=True):
                st.markdown(f"### ➕ {label_add}")
                novo = st.text_input("Digite aqui", key=f"cfg_in_{key_prefix}", label_visibility="collapsed")
                if st.button(f"Salvar", key=f"cfg_btn_add_{key_prefix}", width="stretch"):
                    if novo and novo not in st.session_state[session_key]:
                        st.session_state[session_key].append(novo)
                        st.rerun()
            with st.container(border=True):
                st.markdown(f"### 🗑️ {label_rm}")
                item_rm = st.selectbox("Selecione", st.session_state[session_key], key=f"cfg_sel_rm_{key_prefix}", label_visibility="collapsed")
                if st.button("Excluir", key=f"cfg_btn_rm_{key_prefix}", width="stretch"):
                    if len(st.session_state[session_key]) > 1:
                        st.session_state[session_key].remove(item_rm)
                        st.rerun()

    def render_config_dict(dict_key, cat_options_key, label_tabela, label_add, key_prefix):
        col_tabela, col_acoes = st.columns([1, 1], gap="large")
        with col_tabela:
            st.subheader(label_tabela)
            dados_view = [{"Item": k, "Categoria": v} for k, v in st.session_state[dict_key].items()]
            st.dataframe(dados_view, hide_index=True, width="stretch")
        
        with col_acoes:
            with st.container(border=True):
                st.markdown(f"### ➕ {label_add}")
                novo_nome = st.text_input("Nome", key=f"cfg_n_{key_prefix}")
                nova_cat = st.selectbox("Categoria", st.session_state[cat_options_key], key=f"cfg_c_{key_prefix}")
                if st.button(f"Salvar", key=f"cfg_btn_add_{key_prefix}", width="stretch"):
                    if novo_nome:
                        st.session_state[dict_key][novo_nome] = nova_cat
                        st.rerun()
            
            with st.container(border=True):
                st.markdown(f"### 🗑️ Remover")
                item_rm = st.selectbox("Selecione", list(st.session_state[dict_key].keys()), key=f"cfg_rm_{key_prefix}")
                if st.button("Excluir", key=f"cfg_btn_rm_{key_prefix}", width="stretch"):
                    if len(st.session_state[dict_key]) > 1:
                        del st.session_state[dict_key][item_rm]
                        st.rerun()

    with sub_efetivo:
        render_config_tab("cat_efetivo", "Funções Atuais", "Adicionar Função", "Remover", "func")
    
    with sub_equip_nomes:
        render_config_dict("dict_equipamentos", "cat_equip_tipo", "Equipamentos", "Novo Equipamento", "eq")
        
    with sub_equip_tipo:
        render_config_tab("cat_equip_tipo", "Tipos de Equipamento", "Novo Tipo", "Remover Tipo", "eq_tipo")
        
    with sub_gastos_itens:
        render_config_dict("dict_gastos", "cat_gastos_categorias", "Itens de Gasto", "Novo Item", "gt")
        
    with sub_gastos_cat:
        render_config_tab("cat_gastos_categorias", "Categorias de Gasto", "Nova Categoria", "Remover Categoria", "gt_cat")

# ── ORÇAMENTOS ────────────────────────────────────────────────────────────────

elif menu_selecionado == "Orçamentos":
    st.title("📋 Gestão de Orçamentos")
    st.write("Crie e gerencie propostas comerciais (Funil de Vendas).")
    st.divider()

    col_lista, col_novo = st.columns([1.5, 1], gap="large")

    with col_novo:
        with st.container(border=True):
            st.subheader("➕ Novo Orçamento")
            
            with st.form("form_novo_orcamento", clear_on_submit=True):
                input_cliente = st.text_input("Nome do Cliente", placeholder="Ex: João da Silva")
                input_projeto = st.text_input("Nome do Projeto", placeholder="Ex: Reforma do Telhado")
                
                st.markdown("##### 💰 Estimativa de Custos")
                custo_mat = st.number_input("Custo de Materiais (R$)", min_value=0.0, step=100.0, format="%.2f", value=None, placeholder="Digite o valor...")
                custo_mao = st.number_input("Custo de Mão de Obra (R$)", min_value=0.0, step=100.0, format="%.2f", value=None, placeholder="Digite o valor...")

                st.markdown("##### 📈 Lucro")
                lucro_pct = st.number_input("Markup sobre o custo (%)", min_value=0.0, step=1.0, format="%.1f", value=None, placeholder="Ex: 20.0", help="Porcentagem aplicada sobre a soma de materiais e mão de obra. O lucro é gravado em reais.")

                btn_salvar_orc = st.form_submit_button("💾 Gerar Orçamento", width="stretch")

                if btn_salvar_orc:
                    if input_cliente and input_projeto:
                        val_mat = custo_mat if custo_mat is not None else 0.0
                        val_mao = custo_mao if custo_mao is not None else 0.0
                        val_markup = lucro_pct if lucro_pct is not None else 0.0

                        # A API recebe o lucro em reais e calcula o valor total.
                        subtotal = val_mat + val_mao
                        lucro_reais = round(subtotal * val_markup / 100, 2)

                        pacote_orcamento = {
                            "cliente": input_cliente,
                            "nome_projeto": input_projeto,
                            "custo_material": val_mat,
                            "custo_mao_de_obra": val_mao,
                            "lucro": lucro_reais,
                        }
                        
                        try:
                            resp = requests.post(f"{API_URL}/orcamentos/", json=pacote_orcamento)
                            if resp.status_code == 200:
                                st.success("Orçamento gerado com sucesso!")
                                st.rerun()
                            else:
                                detalhes_erro = resp.json() 
                                st.error(f"Erro {resp.status_code} da API: {detalhes_erro}")
                        except Exception as e:
                            st.error(f"Erro de conexão com a API: {e}")
                    else:
                        st.warning("Preencha o nome do cliente e do projeto.")


    with col_lista:
        st.subheader("🗂️ Orçamentos Recentes")
        
        try:
            resp_lista = requests.get(f"{API_URL}/orcamentos/")
            orcamentos = resp_lista.json() if resp_lista.status_code == 200 else []
        except:
            orcamentos = []

        if not orcamentos:
            st.info("Nenhum orçamento cadastrado ainda.")
        else:
            opcoes_busca = [f"{orc['cliente']} - {orc['nome_projeto']}" for orc in orcamentos]

            # Sem seleção, a lista mostra todos; o "×" da caixa limpa a busca.
            orcamento_selecionado = st.selectbox("🔍 Orçamento", opcoes_busca, index=None, key="busca_orcamentos",
                                                 placeholder="Todos os orçamentos — digite para buscar…")
            
            st.markdown("<br>", unsafe_allow_html=True) 

            if orcamento_selecionado:
                orcamentos = [
                    orc for orc in orcamentos 
                    if f"{orc['cliente']} - {orc['nome_projeto']}" == orcamento_selecionado
                ]

            for orc in reversed(orcamentos):
                with st.container(border=True):
                    col_info, col_status = st.columns([3, 1])
                    
                    with col_info:
                        st.markdown(f"#### {orc['nome_projeto']}")
                        st.caption(f"👤 Cliente: **{orc['cliente']}**")
                        
                        custo = orc.get('custo_material', 0) + orc.get('custo_mao_de_obra', 0)
                        lucro = orc.get('lucro', 0)
                        markup = lucro / custo * 100 if custo else 0.0

                        st.markdown(f"""
                            <div style="font-size:14px; margin-bottom: 8px;">
                                🧱 <b>Materiais:</b> <code>{reais(orc.get('custo_material', 0))}</code><br>
                                👷 <b>Mão de Obra:</b> <code>{reais(orc.get('custo_mao_de_obra', 0))}</code><br>
                                📈 <b>Lucro:</b> <code>{reais(lucro)}</code> (markup de {markup:.1f}% sobre o custo)
                            </div>
                        """, unsafe_allow_html=True)

                        st.write(f"💰 **Valor Total:** `{reais(orc.get('valor_total', 0))}`")
                        
                    with col_status:
                        cor_status = "blue"
                        if orc['status'] == "Aprovado": cor_status = "green"
                        elif orc['status'] == "Recusado": cor_status = "red"
                        elif orc['status'] == "Convertido em Obra": cor_status = "orange"
                        
                        st.markdown(f"Status:<br>:{cor_status}[**{orc['status']}**]", unsafe_allow_html=True)
                        
                        if orc['status'] == "Em análise":
                            if st.button("✅ Aprovar", key=f"aprovar_{orc['id']}", width="stretch", type="primary"):
                                requests.put(f"{API_URL}/orcamentos/{orc['id']}/status", json={"status": "Aprovado"})
                                st.rerun()
                                
                            if st.button("❌ Recusar", key=f"negar_{orc['id']}", width="stretch"):
                                requests.put(f"{API_URL}/orcamentos/{orc['id']}/status", json={"status": "Recusado"})
                                st.rerun()
                                
                        elif orc['status'] == "Aprovado":
                            with st.popover("🚀 Iniciar Obra", width="stretch"):
                                st.markdown("### Finalizar Cadastro")
                                st.write("Preencha os dados logísticos para iniciar a obra.")
                                
                                end_obra = st.text_input("Endereço da Obra", key=f"end_{orc['id']}")
                                
                                col_pop1, col_pop2 = st.columns(2)
                                with col_pop1:
                                    amb_obra = st.selectbox(
                                        "Ambiente",
                                        list(ROTULO_AMBIENTE),
                                        format_func=ROTULO_AMBIENTE.get,
                                        key=f"amb_{orc['id']}"
                                    )
                                with col_pop2:
                                    dt_obra = st.date_input("Data de Início", key=f"dt_{orc['id']}")
                                
                                if st.button("Confirmar e Criar Obra", key=f"confirm_{orc['id']}", width="stretch", type="primary"):
                                    if end_obra:
                                        payload = {
                                            "endereco": end_obra,
                                            "ambiente": amb_obra,
                                            "data_inicio": str(dt_obra)
                                        }
                                        resp = requests.post(
                                            f"{API_URL}/orcamentos/{orc['id']}/converter", 
                                            json=payload
                                        )
                                        
                                        if resp.status_code == 200:
                                            st.toast("🎉 Obra enviada para o Painel!")
                                            st.rerun()
                                        else:
                                            st.error("Erro na conversão.")
                                    else:
                                        st.warning("O endereço é obrigatório.")