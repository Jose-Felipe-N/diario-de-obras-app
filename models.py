from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship

#Base que todas tabelas vão herdar
Base = declarative_base()

class Obra(Base):
    __tablename__ = "obras"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String)
    data_inicio = Column(Date)
    status = Column(String, default="Em andamento")
    ambiente = Column(String, default="Aberto")

    diarios = relationship("DiarioDeObra", back_populates="obra")

class DiarioDeObra(Base):
    __tablename__ = "diarios_de_obra"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    clima_manha = Column(String)
    clima_tarde = Column(String)
    observacoes_gerais = Column(Text)
    local_dia = Column(String, nullable=True)
    obra_id = Column(Integer, ForeignKey("obras.id"))
    
    obra = relationship("Obra", back_populates="diarios")
    efetivos = relationship("Efetivo", back_populates="diario", cascade="all, delete-orphan")
    equipamentos = relationship("Equipamento", back_populates="diario", cascade="all, delete-orphan")
    gastos = relationship("Gasto", back_populates="diario", cascade="all, delete-orphan") # Faltava essa linha!

class Efetivo(Base):
    __tablename__ = "efetivos"
    
    id = Column(Integer, primary_key=True, index=True)
    funcao = Column(String)
    quantidade = Column(Integer)
    horas_trabalhadas = Column(Float)

    diario_id = Column(Integer, ForeignKey("diarios_de_obra.id"))
    diario = relationship("DiarioDeObra", back_populates="efetivos")

class Equipamento(Base):
    __tablename__ = "equipamentos"

    id = Column(Integer, primary_key=True, index=True)
    nome_item = Column(String)
    tipo = Column(String)
    quantidade = Column(Integer)
    
    diario_id = Column(Integer, ForeignKey("diarios_de_obra.id"))
    diario = relationship("DiarioDeObra", back_populates="equipamentos")

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String)
    categoria = Column(String)
    valor = Column(Float)

    diario_id = Column(Integer, ForeignKey("diarios_de_obra.id"))
    diario = relationship("DiarioDeObra", back_populates="gastos")

class orcamento(Base):
    __tablename__ = "orcamentos"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String, nullable=False)
    nome_projeto = Column(String, nullable=False)
    custo_material = Column(Float, default=0.0)
    custo_mao_de_obra = Column(Float, default=0.0)
    lucro = Column(Float, default=0.0)
    valor_total = Column(Float, default=0.0)

    status = Column(String, default="Em análise")
    