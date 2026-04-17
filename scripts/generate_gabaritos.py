import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODIGOS = ROOT / "Códigos"
PROVAS = ROOT / "provas"


def nb_markdown_cell(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.strip().splitlines()],
    }


def write_notebook(path: Path, sections: list[str]) -> None:
    nb = {
        "cells": [nb_markdown_cell(section) for section in sections],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.x",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")


def wrap_text(text: str, width: int = 95) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            raw,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.extend(wrapped or [""])
    return lines


def pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def write_simple_pdf(path: Path, title: str, sections: list[str]) -> None:
    full_text = [title, "", *sum([wrap_text(section) + [""] for section in sections], [])]
    pages: list[list[str]] = []
    current: list[str] = []
    max_lines = 46
    for line in full_text:
        current.append(line)
        if len(current) >= max_lines:
            pages.append(current)
            current = []
    if current:
        pages.append(current)

    objects: list[bytes] = []

    def add_object(data: str | bytes) -> int:
        payload = data.encode("latin-1", errors="replace") if isinstance(data, str) else data
        objects.append(payload)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_ids: list[int] = []
    page_ids: list[int] = []
    for page_lines in pages:
        stream_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for idx, line in enumerate(page_lines):
            prefix = "" if idx == 0 else "T* "
            stream_lines.append(f"{prefix}({pdf_escape(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        content_ids.append(content_id)

    for content_id in content_ids:
        page_id = add_object(
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_id = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")

    for page_id in page_ids:
        objects[page_id - 1] = objects[page_id - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_id} 0 R".encode("ascii"))

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode(
            "ascii"
        )
    )
    path.write_bytes(pdf)


MAIN_SECTIONS = [
    """
# Gabarito - P1 Banco de Dados Não Relacional 20261

Material preparado em formato de gabarito comentado. No caso da prova principal, há um detalhe importante na massa de dados:

- alguns valores foram cadastrados com espaços extras, como `" básico "` e `" documentário "`;
- por isso, o gabarito abaixo informa a alternativa oficialmente correta e também observa o efeito prático desses dados na execução.
""",
    """
## Questão 1 - Modelagem: Embed vs Reference

### Resposta

- Vantagem do modelo A (Embed): a leitura é simples e rápida porque os dados do usuário e seu histórico ficam no mesmo documento. Em uma única consulta é possível recuperar o perfil e os filmes assistidos, sem precisar de junção.
- Limitação do modelo A: se o histórico crescer demais, o documento pode ficar muito grande e se aproximar do limite de 16 MB do MongoDB. Além disso, documentos muito grandes aumentam custo de leitura e atualização.
- Melhor cenário para o modelo B (Reference com `$lookup`): quando o histórico cresce muito, precisa ser consultado separadamente, ou quando o mesmo conjunto de dados precisa ser reutilizado com mais flexibilidade.
- Comando correto do modelo B:

```javascript
db.usuarios.aggregate([
  {
    $lookup: {
      from: "historico_filmes",
      localField: "_id",
      foreignField: "usuario_id",
      as: "historico"
    }
  },
  { $match: { nome: "Ana Lima" } }
])
```

### Interpretação

O `$lookup` faz uma junção entre `usuarios` e `historico_filmes`, anexando ao documento de Ana um array `historico` com os registros relacionados ao `_id` dela.
""",
    """
## Questão 2 - Script Python: lógica de atualização

### Resposta

- Erro crítico da implementação B: ela usa `update_many({}, ...)`, ou seja, atualiza todos os documentos da coleção, não apenas o usuário corrente do laço.
- Consequência: cada iteração poderia empurrar `"top_reviewer"` para todos os usuários, contaminando a base inteira e ainda gerando duplicidades por usar `$push`.
- A implementação A usa `$addToSet` porque esse operador só adiciona o valor se ele ainda não estiver presente no array.
- Diferença prática:
  - `$addToSet`: evita repetição.
  - `$push`: sempre adiciona, mesmo se o valor já existir.

### Resultado esperado da implementação A com a massa fornecida

A consulta seleciona usuários com `plano = "premium"` e `ativo = true`. Na massa enviada, isso retorna apenas Ana Lima.

Média de Ana:

`(9.5 + 8.0) / 2 = 8.75`

Como `8.75 < 9.0`, ninguém recebe a tag.

Relatório interpretado:

- nenhum usuário recebeu `"top_reviewer"` com os dados atuais.
""",
    """
## Questão 3 - Limpeza de dados com delete

### Resposta

- O comando correto é o **Comando X**:

```javascript
db.usuarios.deleteMany({
  ativo: false,
  historico: { $size: 0 }
})
```

- Justificativa: ele aplica as duas condições ao mesmo tempo, ou seja, usuários inativos **E** com histórico vazio.
- O comando Y é perigoso porque usa `$or`. Assim, removeria usuários que fossem apenas inativos ou apenas tivessem histórico vazio.
- Diferença entre `deleteOne` e `deleteMany`:
  - `deleteOne` remove apenas o primeiro documento compatível.
  - `deleteMany` remove todos os documentos compatíveis.

### Resultados esperados

Antes do delete:

```javascript
db.usuarios.countDocuments({
  ativo: false,
  historico: { $size: 0 }
})
```

Resultado esperado: `2`

Delete:

```javascript
db.usuarios.deleteMany({
  ativo: false,
  historico: { $size: 0 }
})
```

Resultado esperado: `deletedCount: 2`

Depois do delete:

```javascript
db.usuarios.countDocuments({
  ativo: false,
  historico: { $size: 0 }
})
```

Resultado esperado: `0`

Interpretação: Carla Mendes e Felipe Nunes seriam removidos.
""",
    """
## Questão 4 - Aggregation Pipeline

### Resposta

- A ordem dos estágios importa porque cada estágio trabalha sobre o resultado do estágio anterior.
- No pipeline incorreto, o `$group` vem antes do `$match`. Depois do agrupamento, o campo `disponivel` deixa de existir nos documentos resultantes. Por isso o `$match` não encontra nada.
- Função de cada estágio:
  - `$match`: filtra documentos.
  - `$group`: agrupa documentos e calcula agregações.
  - `$sort`: ordena o resultado.

### Pipeline correto

```javascript
db.filmes.aggregate([
  { $match: { disponivel: true } },
  {
    $group: {
      _id: "$genero",
      nota_media_genero: { $avg: "$nota_media" }
    }
  },
  { $sort: { nota_media_genero: -1 } }
])
```

### Comparação dos resultados

- Pipeline apresentado: retorna vazio.
- Pipeline corrigido: retorna os gêneros disponíveis com média correta.

### Resultado esperado do pipeline correto

- `anime`: `9.8`
- ` documentário `: `9.5`
- `sci-fi`: `9.0`

Interpretação: entre os conteúdos disponíveis, anime tem a maior média. Também vale observar que o gênero documentário foi salvo com espaços extras na base.
""",
    """
## Questão 5 - Operadores de comparação e arrays

### Alternativa correta

**(a)**

```javascript
db.usuarios.find(
  { ativo: true, interesses: { $in: ["sci-fi", "documentário"] }, idade: { $gte: 18 } },
  { nome: 1, idade: 1, interesses: 1, _id: 0 }
)
```

### Justificativa

- `(a)` está correta porque usa `$in`, filtra usuários ativos, exige idade maior ou igual a 18 e projeta os campos pedidos sem `_id`.
- `(b)` exige igualdade exata do array e ainda usa `$gt: 18`, excluindo idade 18.
- `(c)` filtra corretamente por interesse e idade, mas não faz a projeção pedida.
- `(d)` usa `$all`, o que exige a presença simultânea de todos os valores.

### Resultado esperado

Com a massa atual, os usuários que atendem são:

- Ana Lima
- Diego Ramos

### Questão reflexiva

Para buscar apenas usuários com mais de 22 anos:

```javascript
idade: { $gt: 22 }
```

- `$gte` significa maior ou igual.
- `$gt` significa estritamente maior.

Com esse ajuste, Diego Ramos deixa de aparecer e sobra apenas Ana Lima.
""",
    """
## Questão 6 - Inserção em arrays sem duplicidade

### Alternativa correta

**(b)**

```python
col.update_one(
    {"nome": "Diego Ramos"},
    {"$addToSet": {"historico": {"titulo": "Cosmos", "nota": 9.8}}}
)
```

### Justificativa

- `(b)` é a alternativa esperada porque `$addToSet` evita inserir o mesmo valor mais de uma vez.
- `(a)` com `$push` permitiria duplicação.
- `(c)` com `$set` substituiria o campo `historico`.
- `(d)` usa operador inexistente.

### Observação técnica importante

Na massa da prova, Diego já possui `"Cosmos"` no histórico, mas com o campo `assistido_em`. Como o objeto não é idêntico ao novo objeto proposto, o MongoDB ainda pode considerar isso diferente. Se a intenção for evitar duplicidade por título, o ideal seria outra estratégia de modelagem ou filtro.
""",
    """
## Questão 7 - Atualização em massa com $set

### Alternativa correta

**(a)**

```javascript
db.usuarios.updateMany(
  { plano: "básico", ativo: true },
  { $set: { plano: "standard", data_upgrade: new Date() } }
)
```

### Justificativa

- `(a)` é a alternativa correta porque atualiza todos os usuários que atendem ao filtro e registra a data.
- `(b)` atualiza apenas um documento.
- `(c)` usa forma antiga e incompleta.
- `(d)` usa `$inc` em um campo textual, o que está errado.

### Observação técnica importante

Na massa fornecida, o valor salvo foi `" básico "` com espaços extras. Em execução literal, seria necessário limpar os dados ou consultar exatamente esse valor.
""",
    """
## Questão 8 - Pipeline de agregação com duplo $match

### Alternativa correta

**(a)**

```javascript
db.filmes.aggregate([
  { $match: { disponivel: true } },
  {
    $group: {
      _id: "$genero",
      media_dur: { $avg: "$duracao_min" },
      nota: { $avg: "$nota_media" }
    }
  },
  { $match: { nota: { $gt: 9.0 } } }
])
```

### Resultado esperado

- `anime`: `media_dur = 24`, `nota = 9.8`
- ` documentário `: `media_dur = 43`, `nota = 9.5`

### Justificativa

- `(a)` está correta porque primeiro filtra os filmes disponíveis, depois agrupa e por fim mantém apenas os grupos com média acima de 9.0.
- `(b)` tenta filtrar depois do agrupamento usando campos que já não existem mais nesse formato.
- `(c)` não é sintaxe válida de agregação no MongoDB.
- `(d)` não agrupa nem calcula média.
""",
    """
## Questão 9 - Exclusão com critérios compostos

### Alternativa correta

**(a)**

```javascript
db.usuarios.countDocuments({
  ativo: false,
  historico: { $size: 0 },
  data_cadastro: { $lt: ISODate("2023-01-01") }
})

db.usuarios.deleteMany({
  ativo: false,
  historico: { $size: 0 },
  data_cadastro: { $lt: ISODate("2023-01-01") }
})
```

### Resultado esperado

- Antes da remoção: `1`
- Removidos: `1`
- Depois da remoção: `0`

### Interpretação

A única usuária afetada é Carla Mendes.
""",
    """
## Questão 10 - Projeção e ordenação em Python

### Alternativa correta

**(a)**

```python
db.filmes.find(
    {"disponivel": True},
    {"titulo": 1, "nota_media": 1, "genero": 1, "_id": 0}
).sort("nota_media", -1).limit(3)
```

### Justificativa

- `(a)` filtra, projeta, ordena em ordem decrescente e limita a 3.
- `(b)` ordena em ordem crescente e ainda inclui `_id`.
- `(c)` não filtra por disponibilidade e não projeta `genero`.
- `(d)` usa agregação, mas não cumpre exatamente a implementação pedida em Python com projeção explícita.

### Resultado esperado

Os três filmes disponíveis com maior nota são:

1. Attack on Titan - 9.8 - anime
2. Cosmos - 9.5 - documentário
3. Stranger Things - 9.2 - sci-fi
""",
]


ADAPT_SECTIONS = [
    """
# Gabarito - P1 Banco de Dados Não Relacional 20261 Adapt

Gabarito comentado da versão adaptada da prova.
""",
    """
## Questão 1 - Por que usar NoSQL?

### Alternativa correta

**(a)**

### Justificativa

MongoDB trabalha com esquema flexível, então um documento pode receber um campo novo sem obrigar todos os outros a terem a mesma estrutura.
""",
    """
## Questão 2 - Filtros de velocidade

### Alternativa correta

**(b)**

```javascript
db.personagens.find({ velocidade: { $gt: 80 } })
```

### Interpretação

Esse comando retorna apenas Sonic, porque ele tem velocidade 100. Tails tem exatamente 80 e Knuckles tem 75.
""",
    """
## Questão 3 - Coletando anéis

### Alternativa correta

**(b)**

```javascript
db.personagens.updateOne({ nome: "Tails" }, { $inc: { aneis: 10 } })
```

### Justificativa

- `$inc` soma ao valor atual.
- `$set` substituiria o valor por 10.
""",
    """
## Questão 4 - Busca por habilidades

### Alternativa correta

**(a)**

```javascript
db.personagens.find({ habilidades: { $in: ["Escalar", "Voo"] } })
```

### Interpretação

O operador `$in` busca documentos cujo array contenha pelo menos um dos valores informados. Nesse caso, retornaria Tails e Knuckles.
""",
    """
## Questão 5 - Limpeza de dados

### Alternativa correta

**(a)**

```javascript
db.personagens.deleteOne({ nome: "Knuckles" })
```

### Justificativa

- `deleteOne` remove o documento do personagem.
- `updateOne` apenas alteraria o campo `ativo`.
- `drop()` apagaria a coleção inteira.
""",
    """
## Questão 6 - Python e MongoDB

### Alternativa correta

**(a)**

```python
client = MongoClient("mongodb://localhost:27017")
```

### Justificativa

`client` representa a conexão ativa com o servidor MongoDB. `db` representa o banco escolhido e `col` representa a coleção.
""",
]


def main() -> None:
    CODIGOS.mkdir(exist_ok=True)
    main_ipynb = CODIGOS / "P1_Banco_de_Dados_Não_Relacional_20261_gabarito.ipynb"
    adapt_ipynb = CODIGOS / "P1_Banco_de_Dados_Não_Relacional_20261_Adapt_gabarito.ipynb"
    write_notebook(main_ipynb, MAIN_SECTIONS)
    write_notebook(adapt_ipynb, ADAPT_SECTIONS)

    main_pdf = PROVAS / "P1_Banco_de_Dados_Não_Relacional_20261_gabarito.pdf"
    adapt_pdf = PROVAS / "P1_Banco_de_Dados_Não_Relacional_20261_Adapt_gabarito.pdf"
    write_simple_pdf(main_pdf, "Gabarito - P1 Banco de Dados Não Relacional 20261", MAIN_SECTIONS)
    write_simple_pdf(adapt_pdf, "Gabarito - P1 Banco de Dados Não Relacional 20261 Adapt", ADAPT_SECTIONS)

    print(main_ipynb)
    print(adapt_ipynb)
    print(main_pdf)
    print(adapt_pdf)


if __name__ == "__main__":
    main()
