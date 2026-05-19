import streamlit as st
import requests
import google.generativeai as genai
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Diário de Obras", layout="wide", initial_sidebar_state="expanded")

URL_OBRAS = "http://127.0.0.1:8000/obras/"

if "cat_efetivo" not in st.session_state:
    st.session_state["cat_efetivo"] = ["Servente", "Pedreiro", "Carpinteiro", "Armador", "Eletricista", "Pintor", "Mestre de Obras"]

if "cat_equip_tipo" not in st.session_state:
    st.session_state["cat_equip_tipo"] = ["Ferramenta Manual", "Ferramenta Elétrica", "Maquinário Pesado", "Veículo", "EPI/EPC"]

if "cat_equip_nomes" not in st.session_state:
    st.session_state["cat_equip_nomes"] = ["Betoneira", "Retroescavadeira", "Andaime", "Compactador", "Gerador", "Caminhão", "Guincho"]

if "cat_gastos_categorias" not in st.session_state:
    st.session_state["cat_gastos_categorias"] = ["Material de Construção", "Mão de Obra Externa", "Locação", "Combustível", "Alimentação"]

if "cat_gastos_itens" not in st.session_state:
    st.session_state["cat_gastos_itens"] = ["Cimento", "Areia", "Brita", "Vergalhão", "Tijolo", "Tinta", "Madeira", "Parafuso", "Diesel"]

if "dict_equipamentos" not in st.session_state:
    st.session_state["dict_equipamentos"] = {
        "Betoneira": "Maquinário Pesado", "Retroescavadeira": "Maquinário Pesado",
        "Andaime": "EPI/EPC", "Compactador": "Maquinário Pesado",
        "Gerador": "Ferramenta Elétrica", "Caminhão": "Veículo", "Guincho": "Veículo"
    }

if "dict_gastos" not in st.session_state:
    st.session_state["dict_gastos"] = {
        "Cimento": "Material de Construção", "Areia": "Material de Construção",
        "Brita": "Material de Construção", "Vergalhão": "Material de Construção",
        "Tijolo": "Material de Construção", "Tinta": "Material de Construção",
        "Madeira": "Material de Construção", "Parafuso": "Material de Construção",
        "Diesel": "Combustível"
    }

if "mostrar_painel" not in st.session_state:
    st.session_state["mostrar_painel"] = False

CLIMA_ICONE = {
    "Sol": "☀️",
    "Nublado": "☁️",
    "Chuva": "🌧️",
    "Tempestade": "⛈️",
}

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

with st.sidebar:
    st.title("🏗️ Gestão de Obras")
    st.write("Navegue pelas ferramentas:")
    menu_selecionado = option_menu(
        menu_title=None,
        options=["Início", "Painel de Obras", "Orçamentos", "Nova Obra", "Novo Diário", "Analista IA", "Configurações"],
        icons=["house-fill", "bar-chart-fill", "calculator-fill", "building-fill-add", "journal-text", "robot", "gear-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "orange", "font-size": "18px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#333333"},
            "nav-link-selected": {"background-color": "#005C99"},
        }
    )
    st.divider()
    st.caption("Sistema de Gestão v1.0")

# ── INÍCIO ─────────────────────────────────────────────────────────────────────

if menu_selecionado == "Início":
    st.title("🏠 Início")
    st.write("Bem-vindo ao Centro de Comando de sua construtora.")
    st.divider()
    try:
        resposta = requests.get("http://127.0.0.1:8000/dashboard/")
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
                st.subheader("⚡ Ações Rápidas")
                st.info("💡 Navegue pelo menu lateral para cadastrar novas obras, gerenciar relatórios e preencher os diários do dia.")
        else:
            st.error("Erro ao carregar os dados do painel.")
    except Exception as e:
        st.error(f"Erro de conexão com o servidor: {e}")

# ── PAINEL DE OBRAS ────────────────────────────────────────────────────────────

elif menu_selecionado == "Painel de Obras":
    st.title("📊 Painel de Obras")
    st.write("Visão geral dos relatórios e andamento do canteiro.")

    if st.button("🔄 Atualizar Relatórios"):
        st.session_state["mostrar_painel"] = True
        st.session_state["busca_obra"] = ""

    if st.session_state["mostrar_painel"]:
        try:
            resposta = requests.get(URL_OBRAS)
            if resposta.status_code == 200:
                dados = resposta.json()
                st.divider()

                nomes_obras = [obra['nome'] for obra in dados]
                obra_selecionada = st.selectbox("🔍 Buscar ou selecionar obra:", [""] + nomes_obras, key="busca_obra")

                if obra_selecionada != "":
                    obras_filtradas = [obra for obra in dados if obra['nome'] == obra_selecionada]

                    for obra in obras_filtradas:
                        col_tit, col_del = st.columns([5, 1])
                        with col_tit:
                            st.subheader(f"🏢 Obra: {obra['nome']}")
                        with col_del:
                            if st.button("🗑️ Excluir Obra", key=f"del_obra_{obra['id']}"):
                                resp_del = requests.delete(f"http://127.0.0.1:8000/obras/{obra['id']}")
                                if resp_del.status_code == 200:
                                    st.success("Obra removida!")
                                    st.rerun()

                        st.write(f"**Endereço:** {obra['endereco']}")
                        st.write(f"**Ambiente:** {obra.get('ambiente', 'Não informado')}")

                        col_status, col_btn = st.columns([3, 1])
                        with col_status:
                            lista_status = ["Planejamento", "Em andamento", "Pausada", "Concluída"]
                            index_atual = lista_status.index(obra['status']) if obra['status'] in lista_status else 0
                            novo_status = st.selectbox("Status Atual:", lista_status, index=index_atual, key=f"sel_status_{obra['id']}")
                        with col_btn:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("Atualizar Status", key=f"btn_status_{obra['id']}"):
                                resp_put = requests.put(
                                    f"http://127.0.0.1:8000/obras/{obra['id']}/status",
                                    json={"status": novo_status}
                                )
                                if resp_put.status_code == 200:
                                    st.success("Status atualizado!")
                                    st.rerun()

                        st.markdown("<br>", unsafe_allow_html=True)

                        if not obra['diarios']:
                            st.info("Nenhum diário registrado para esta obra.")

                        if "diario_aberto" not in st.session_state:
                            st.session_state["diario_aberto"] = None

                        for diario in obra['diarios']:
                            clima_m = diario.get('clima_manha', 'Sol')
                            clima_t = diario.get('clima_tarde', 'Sol')
                            icone_m = CLIMA_ICONE.get(clima_m, "🌤️")
                            icone_t = CLIMA_ICONE.get(clima_t, "🌤️")

                            total_trabalhadores = sum(e['quantidade'] for e in diario.get('efetivos', []))
                            total_gastos = sum(g['valor'] for g in diario.get('gastos', []))
                            total_gastos_fmt = f"R$ {total_gastos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                            label_expander = (
                                f"📅  {diario['data']}   |   "
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
                                        if st.button("💾 Salvar", key=f"save_ed_{diario['id']}", use_container_width=True):
                                            requests.put(
                                                f"http://127.0.0.1:8000/diarios/{diario['id']}",
                                                json={"clima_manha": edit_m, "clima_tarde": edit_t, "observacoes_gerais": edit_obs}
                                            )
                                            st.success("Diário atualizado!")
                                            st.rerun()
                                    with col_e2:
                                        if st.button("🗑️ Excluir", key=f"del_dia_{diario['id']}", use_container_width=True, type="primary"):
                                            requests.delete(f"http://127.0.0.1:8000/diarios/{diario['id']}")
                                            st.success("Diário removido!")
                                            st.rerun()


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
                    st.info("👆 Selecione uma obra para visualizar, editar ou excluir.")
            else:
                st.error("Erro ao buscar dados.")
        except Exception as e:
            st.error(f"Erro: {e}")

# ── NOVA OBRA ──────────────────────────────────────────────────────────────────

elif menu_selecionado == "Nova Obra":
    st.title("➕ Cadastrar Nova Obra")
    st.write("Preencha os dados abaixo para iniciar um novo projeto.")
    with st.form("form_nova_obra", clear_on_submit=True):
        input_nome = st.text_input("Nome da Obra")
        input_endereco = st.text_input("Endereço Completo")
        col1, col2 = st.columns(2)
        with col1:
            input_data = st.date_input("Data de Início")
        with col2:
            input_status = st.selectbox("Status Atual", ["Planejamento", "Em andamento", "Pausada", "Concluída"])
        st.markdown("**Condições do Local:**")
        input_ambiente = st.radio(
            "Selecione o tipo de ambiente da obra:",
            ["Aberto (Sujeito ao clima)", "Fechado (Coberto)", "Misto (Aberto e Fechado)"],
            horizontal=True
        )
        btn_salvar = st.form_submit_button("💾 Salvar Obra")
        if btn_salvar:
            pacote_dados = {"nome": input_nome, "endereco": input_endereco, "data_inicio": str(input_data), "status": input_status, "ambiente": input_ambiente}
            try:
                resposta_post = requests.post(URL_OBRAS, json=pacote_dados)
                if resposta_post.status_code == 200:
                    st.success(f"✨ A obra '{input_nome}' foi criada com sucesso!")
                else:
                    st.error("Erro ao tentar salvar a obra. Verifique os dados.")
            except Exception as e:
                st.error("Erro de conexão com a API.")

# ── NOVO DIÁRIO ────────────────────────────────────────────────────────────────
elif menu_selecionado == "Novo Diário":
    st.title("📝 Preencher Diário de Obra")
    try:
        resp_obras = requests.get(URL_OBRAS)
        obras_disponiveis = resp_obras.json() if resp_obras.status_code == 200 else []
    except:
        obras_disponiveis = []

    if not obras_disponiveis:
        st.warning("⚠️ Você precisa cadastrar pelo menos uma Obra antes de criar um Diário.")
    else:
        opcoes_formatadas = {"Selecione uma obra...": None}
        for o in obras_disponiveis:
            opcoes_formatadas[f"{o['id']} - {o['nome']}"] = o
        escolha = st.selectbox("Selecione a Obra", list(opcoes_formatadas.keys()))

        if escolha != "Selecione uma obra...":
            obra_selecionada = opcoes_formatadas[escolha]

            with st.expander("⚙️ Gerenciar Categorias Rápidas"):
                col_add1, col_add2, col_add3 = st.columns(3)
                with col_add1:
                    st.markdown("**👷 Efetivo**")
                    nova_func = st.text_input("Nova Função", key="in_func")
                    if st.button("➕ Add", key="btn_add_func"):
                        if nova_func and nova_func not in st.session_state["cat_efetivo"]:
                            st.session_state["cat_efetivo"].append(nova_func)
                            st.rerun()
                    func_remover = st.selectbox("Remover Função", st.session_state["cat_efetivo"], key="sel_rm_func")
                    if st.button("🗑️ Remover", key="btn_rm_func"):
                        if len(st.session_state["cat_efetivo"]) > 1:
                            st.session_state["cat_efetivo"].remove(func_remover)
                            st.rerun()
                        else:
                            st.error("Mantenha pelo menos uma opção.")
                with col_add2:
                    st.markdown("**🚜 Equipamentos**")
                    novo_eq_nome = st.text_input("Novo Equipamento", key="in_eq_nome")
                    nova_eq_cat = st.selectbox("Categoria do Equip.", st.session_state["cat_equip_tipo"], key="in_eq_cat")
                    
                    if st.button("➕ Add Equipamento", key="btn_add_eq_nome"):
                        if novo_eq_nome and novo_eq_nome not in st.session_state["dict_equipamentos"]:
                            st.session_state["dict_equipamentos"][novo_eq_nome] = nova_eq_cat
                            st.success(f"{novo_eq_nome} adicionado!")
                            st.rerun()

                with col_add3:
                    st.markdown("**💰 Gastos**")
                    novo_gasto_item = st.text_input("Novo Item de Gasto", key="in_gasto_item")
                    nova_gasto_cat = st.selectbox("Categoria do Gasto", st.session_state["cat_gastos_categorias"], key="in_gasto_cat")
                    
                    if st.button("➕ Add Item", key="btn_add_gasto_item"):
                        if novo_gasto_item and novo_gasto_item not in st.session_state["dict_gastos"]:
                            st.session_state["dict_gastos"][novo_gasto_item] = nova_gasto_cat
                            st.success(f"{novo_gasto_item} adicionado!")
                            st.rerun()
                    gasto_item_remover = st.selectbox("Remover Item", st.session_state["cat_gastos_itens"], key="sel_rm_gasto_item")
                    if st.button("🗑️ Remover Item", key="btn_rm_gasto_item"):
                        if len(st.session_state["cat_gastos_itens"]) > 1:
                            st.session_state["cat_gastos_itens"].remove(gasto_item_remover)
                            st.rerun()
                        else:
                            st.error("Mantenha pelo menos uma opção.")

            with st.form("form_novo_diario", clear_on_submit=True):
                st.info(f"Preenchendo diário para: **{obra_selecionada['nome']}**")
                data_diario = st.date_input("Data do Diário")
                col_clima1, col_clima2 = st.columns(2)
                with col_clima1:
                    clima_manha = st.selectbox("Clima (Manhã)", ["Sol", "Chuva", "Nublado", "Tempestade"])
                with col_clima2:
                    clima_tarde = st.selectbox("Clima (Tarde)", ["Sol", "Chuva", "Nublado", "Tempestade"])

                local_dia = None
                ambiente_obra = obra_selecionada.get("ambiente")
                if ambiente_obra == "Misto (Aberto e Fechado)":
                    st.markdown("### 📍 Localização do Trabalho")
                    local_dia = st.radio("Onde a maior parte do trabalho foi realizada hoje?", ["Interior (Coberto)", "Exterior (Céu Aberto)"], horizontal=True)
                elif ambiente_obra == "Fechado (Coberto)":
                    local_dia = "Interior (Coberto)"
                    st.info("ℹ️ Obra em ambiente fechado. Localização definida automaticamente como Interior.")
                else:
                    local_dia = "Exterior (Céu Aberto)"
                    st.info("ℹ️ Obra em ambiente aberto. Localização definida automaticamente como Exterior.")

                observacoes = st.text_area("Observações Gerais")

                st.markdown("### 👷 Trabalhadores (Efetivo)")
                tabela_trabalhadores = st.data_editor(
                    [{"funcao": st.session_state["cat_efetivo"][0], "quantidade": 1, "horas_trabalhadas": 8}],
                    num_rows="dynamic", hide_index=True, key="ed_trab",
                    column_config={
                        "funcao": st.column_config.SelectboxColumn("Função", options=st.session_state["cat_efetivo"], required=True),
                        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, required=True),
                        "horas_trabalhadas": st.column_config.NumberColumn("Horas Trabalhadas", min_value=0.5, step=0.5, required=True),
                    }
                )

                st.markdown("### 🚜 Equipamentos")
                opcoes_equip = list(st.session_state["dict_equipamentos"].keys())
                tabela_equipamentos = st.data_editor(
                    [{"nome_item": opcoes_equip[0], "quantidade": 1}],
                    num_rows="dynamic", hide_index=True, key="ed_equip",
                    column_config={
                        "nome_item": st.column_config.SelectboxColumn("Equipamento", options=opcoes_equip, required=True),
                        "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, required=True),
                    }
                )

                st.markdown("### 💰 Controle Financeiro (Gastos do Dia)")
                opcoes_gastos = list(st.session_state["dict_gastos"].keys())
                tabela_gastos = st.data_editor(
                    [{"item": opcoes_gastos[0], "valor": 0}],
                    num_rows="dynamic", hide_index=True, key="ed_gastos",
                    column_config={
                        "item": st.column_config.SelectboxColumn("Descrição", options=opcoes_gastos, required=True),
                        "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0.0, step=0.01, format="R$ %.2f", required=True),
                    }
                )

                btn_salvar_diario = st.form_submit_button("📝 Salvar Diário")
                if btn_salvar_diario:
                    obra_id_real = obra_selecionada["id"]
                    pacote_diario = {"data": str(data_diario), "clima_manha": clima_manha, "clima_tarde": clima_tarde, "observacoes_gerais": observacoes, "local_dia": local_dia, "obra_id": obra_id_real}
                    try:
                        resposta_diario = requests.post("http://127.0.0.1:8000/diarios/", json=pacote_diario)
                        if resposta_diario.status_code == 200:
                            diario_criado = resposta_diario.json()
                            diario_id_gerado = diario_criado["id"]
                            for trab in tabela_trabalhadores:
                                if trab.get("funcao") and trab.get("quantidade"):
                                    requests.post("http://127.0.0.1:8000/efetivos/", json={**trab, "diario_id": diario_id_gerado})
                            for equip in tabela_equipamentos:
                                if equip.get("nome_item") and equip.get("quantidade"):
                                    tipo_automatico = st.session_state["dict_equipamentos"].get(equip["nome_item"], "Outros")
                                    
                                    requests.post("http://127.0.0.1:8000/equipamentos/", json={
                                        "nome_item": equip["nome_item"],
                                        "tipo": tipo_automatico,
                                        "quantidade": equip["quantidade"],
                                        "diario_id": diario_id_gerado
                                    })
                                    
                            for gasto in tabela_gastos:
                                if gasto.get("item") and gasto.get("valor", 0) > 0:
                                    cat_automatica = st.session_state["dict_gastos"].get(gasto["item"], "Outros")
                                    
                                    requests.post("http://127.0.0.1:8000/gastos/", json={
                                        "item": gasto["item"],
                                        "categoria": cat_automatica,
                                        "valor": gasto["valor"],
                                        "diario_id": diario_id_gerado
                                    })
                            st.success("✨ Diário registrado com sucesso!")
                        else:
                            st.error("Erro ao registrar a capa do diário.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
        else:
            st.info("👆 Selecione uma obra na caixa acima para começar.")

# ── ANALISTA IA ────────────────────────────────────────────────────────────────
elif menu_selecionado == "Analista IA":
    st.markdown("## 🧠 Analista IA")
    st.markdown("Converse com o sistema sobre o andamento das obras, gastos e uso de equipamentos.")

    try:
        res_obras = requests.get("http://127.0.0.1:8000/ia/obras_disponiveis")
        lista_obras = res_obras.json() if res_obras.status_code == 200 else []
    except:
        lista_obras = []

    opcoes_obras = {"🌍 Visão Geral (Todas as Obras)": None}
    for o in lista_obras:
        opcoes_obras[f"🏗️ {o['nome']}"] = o["id"]

    st.markdown("### 🎯 Foco da Análise")
    obra_selecionada_nome = st.selectbox("Escolha a obra para a IA focar:", list(opcoes_obras.keys()))
    obra_selecionada_id = opcoes_obras[obra_selecionada_nome]
    
    st.divider() 

    if "mensagens_chat" not in st.session_state:
        st.session_state["mensagens_chat"] = []

    for msg in st.session_state["mensagens_chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta = st.chat_input("Ex: Temos alguma obra com status de atraso?")

    if pergunta:
        st.session_state["mensagens_chat"].append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Analisando o banco de dados..."):
                try:
                    historico_envio = st.session_state["mensagens_chat"][:-1]

                    resposta_api = requests.post(
                        "http://127.0.0.1:8000/ia/chat",
                        json={
                            "mensagem": pergunta,
                            "historico": historico_envio,
                            "obra_id": obra_selecionada_id  
                        }
                    )
                    
                    


                    if resposta_api.status_code == 200:
                        dados_resposta = resposta_api.json()
                        texto_resposta = dados_resposta.get("resposta", "Erro ao ler a mensagem.")
                        tem_grafico = dados_resposta.get("gerar_grafico", False)
                        
                        st.markdown(texto_resposta)
                        
                        if tem_grafico and "dados_grafico" in dados_resposta:
                                st.markdown(f"**📊 {dados_resposta.get('titulo_grafico', 'Gráfico Analítico')}**")
                                
                                tipo_grafico = dados_resposta.get("tipo_grafico", "barras").lower()
                                
                                df_grafico = pd.DataFrame(
                                    list(dados_resposta["dados_grafico"].items()),
                                    columns=["Categoria", "Valor"]
                                )
                                
                                try:
                                    df_grafico["Categoria_Data"] = pd.to_datetime(df_grafico["Categoria"], format="%d/%m/%Y")
                                    df_grafico = df_grafico.sort_values(by="Categoria_Data")
                                    df_grafico = df_grafico.drop(columns=["Categoria_Data"])
                                except Exception:
                                    pass

                                if tipo_grafico == "pizza":
                                    fig = px.pie(df_grafico, values='Valor', names='Categoria', hole=0.3)
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                elif tipo_grafico == "linha":
                                    fig = px.line(df_grafico, x="Categoria", y="Valor", markers=True)
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                else: # Padrão: gráfico de barras
                                    fig = px.bar(df_grafico, x="Categoria", y="Valor")
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        st.session_state["mensagens_chat"].append({"role": "assistant", "content": texto_resposta})
                    else:
                        st.error("Ops! O Analista IA encontrou um erro no banco de dados.")
                except Exception as e:
                    st.error(f"Erro de conexão com o servidor: {e}")


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
            st.dataframe({"Itens": st.session_state[session_key]}, hide_index=True, use_container_width=True)
        with col_acoes:
            with st.container(border=True):
                st.markdown(f"### ➕ {label_add}")
                novo = st.text_input("Digite aqui", key=f"cfg_in_{key_prefix}", label_visibility="collapsed")
                if st.button(f"Salvar", key=f"cfg_btn_add_{key_prefix}", use_container_width=True):
                    if novo and novo not in st.session_state[session_key]:
                        st.session_state[session_key].append(novo)
                        st.rerun()
            with st.container(border=True):
                st.markdown(f"### 🗑️ {label_rm}")
                item_rm = st.selectbox("Selecione", st.session_state[session_key], key=f"cfg_sel_rm_{key_prefix}", label_visibility="collapsed")
                if st.button("Excluir", key=f"cfg_btn_rm_{key_prefix}", use_container_width=True):
                    if len(st.session_state[session_key]) > 1:
                        st.session_state[session_key].remove(item_rm)
                        st.rerun()

    def render_config_dict(dict_key, cat_options_key, label_tabela, label_add, key_prefix):
        col_tabela, col_acoes = st.columns([1, 1], gap="large")
        with col_tabela:
            st.subheader(label_tabela)
            dados_view = [{"Item": k, "Categoria": v} for k, v in st.session_state[dict_key].items()]
            st.dataframe(dados_view, hide_index=True, use_container_width=True)
        
        with col_acoes:
            with st.container(border=True):
                st.markdown(f"### ➕ {label_add}")
                novo_nome = st.text_input("Nome", key=f"cfg_n_{key_prefix}")
                nova_cat = st.selectbox("Categoria", st.session_state[cat_options_key], key=f"cfg_c_{key_prefix}")
                if st.button(f"Salvar", key=f"cfg_btn_add_{key_prefix}", use_container_width=True):
                    if novo_nome:
                        st.session_state[dict_key][novo_nome] = nova_cat
                        st.rerun()
            
            with st.container(border=True):
                st.markdown(f"### 🗑️ Remover")
                item_rm = st.selectbox("Selecione", list(st.session_state[dict_key].keys()), key=f"cfg_rm_{key_prefix}")
                if st.button("Excluir", key=f"cfg_btn_rm_{key_prefix}", use_container_width=True):
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

                st.markdown("##### 📈 Margem")
                lucro_pct = st.number_input("Margem de Lucro / BDI (%)", min_value=0.0, step=1.0, format="%.1f", value=None, placeholder="Ex: 20.0", help="Porcentagem de lucro aplicada sobre a soma dos custos.")

                btn_salvar_orc = st.form_submit_button("💾 Gerar Orçamento", use_container_width=True)

                if btn_salvar_orc:
                    if input_cliente and input_projeto:
                        val_mat = custo_mat if custo_mat is not None else 0.0
                        val_mao = custo_mao if custo_mao is not None else 0.0
                        val_lucro = lucro_pct if lucro_pct is not None else 0.0
                        
                        subtotal = val_mat + val_mao
                        valor_final = subtotal * (1 + (val_lucro / 100))
                        
                        pacote_orcamento = {
                            "cliente": input_cliente,
                            "nome_projeto": input_projeto,
                            "custo_material": val_mat,        
                            "custo_mao_de_obra": val_mao, 
                            "lucro": val_lucro,               
                            "valor_total": valor_final
                        }
                        
                        try:
                            resp = requests.post("http://127.0.0.1:8000/orcamentos/", json=pacote_orcamento)
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
            resp_lista = requests.get("http://127.0.0.1:8000/orcamentos/")
            orcamentos = resp_lista.json() if resp_lista.status_code == 200 else []
        except:
            orcamentos = []

        if not orcamentos:
            st.info("Nenhum orçamento cadastrado ainda.")
        else:
            opcoes_busca = [""] + [f"{orc['cliente']} - {orc['nome_projeto']}" for orc in orcamentos]
            
            orcamento_selecionado = st.selectbox("🔍 Buscar ou selecionar orçamento:", opcoes_busca, key="busca_orcamentos")
            
            st.markdown("<br>", unsafe_allow_html=True) 

            if orcamento_selecionado != "":
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
                        
                        val_mat_fmt = f"R$ {orc.get('custo_material', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        val_mao_fmt = f"R$ {orc.get('custo_mao_de_obra', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        valor_total_fmt = f"R$ {orc.get('valor_total', 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        lucro_pct = orc.get('lucro', 0)
                        
                        st.markdown(f"""
                            <div style="font-size:14px; margin-bottom: 8px;">
                                🧱 <b>Materiais:</b> <code>{val_mat_fmt}</code><br>
                                👷 <b>Mão de Obra:</b> <code>{val_mao_fmt}</code>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.write(f"💰 **Valor Total:** `{valor_total_fmt}` *(Margem: {lucro_pct}%)*")
                        
                    with col_status:
                        cor_status = "blue"
                        if orc['status'] == "Aprovado": cor_status = "green"
                        elif orc['status'] == "Obra Negada": cor_status = "red"
                        elif orc['status'] == "Convertido em Obra": cor_status = "orange"
                        
                        st.markdown(f"Status:<br>:{cor_status}[**{orc['status']}**]", unsafe_allow_html=True)
                        
                        if orc['status'] == "Em análise":
                            if st.button("✅ Aprovar", key=f"aprovar_{orc['id']}", use_container_width=True, type="primary"):
                                requests.put(f"http://127.0.0.1:8000/orcamentos/{orc['id']}/status", json={"status": "Aprovado"})
                                st.rerun()
                                
                            if st.button("❌ Negar", key=f"negar_{orc['id']}", use_container_width=True):
                                requests.put(f"http://127.0.0.1:8000/orcamentos/{orc['id']}/status", json={"status": "Obra Negada"})
                                st.rerun()
                                
                        elif orc['status'] == "Aprovado":
                            with st.popover("🚀 Iniciar Obra", use_container_width=True):
                                st.markdown("### Finalizar Cadastro")
                                st.write("Preencha os dados logísticos para iniciar a obra.")
                                
                                end_obra = st.text_input("Endereço da Obra", key=f"end_{orc['id']}")
                                
                                col_pop1, col_pop2 = st.columns(2)
                                with col_pop1:
                                    amb_obra = st.selectbox(
                                        "Ambiente",
                                        ["Aberto (Sujeito ao clima)", "Fechado (Coberto)", "Misto"],
                                        key=f"amb_{orc['id']}"
                                    )
                                with col_pop2:
                                    dt_obra = st.date_input("Data de Início", key=f"dt_{orc['id']}")
                                
                                if st.button("Confirmar e Criar Obra", key=f"confirm_{orc['id']}", use_container_width=True, type="primary"):
                                    if end_obra:
                                        payload = {
                                            "endereco": end_obra,
                                            "ambiente": amb_obra,
                                            "data_inicio": str(dt_obra)
                                        }
                                        resp = requests.post(
                                            f"http://127.0.0.1:8000/orcamentos/{orc['id']}/converter", 
                                            json=payload
                                        )
                                        
                                        if resp.status_code == 200:
                                            st.toast("🎉 Obra enviada para o Painel!")
                                            st.rerun()
                                        else:
                                            st.error("Erro na conversão.")
                                    else:
                                        st.warning("O endereço é obrigatório.")