# 🧠 Gabarito de Consultas MongoDB – Aula 05

**Banco:** `sistema_escolar`

**Coleções:** `alunos`, `cursos`, `turmas`, `professores`

Objetivo: Fixar *joins*, agregações e KPIs com desafios graduais.

---

## 🟢 Básico

### **1️⃣ Cursos de Engenharia com alunos ativos**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "cursos",
      localField: "curso_id",
      foreignField: "_id",
      as: "curso"
    }
  },
  { $unwind: "$curso" },
  {
    $match: {
      "curso.departamento": /engenharia/i,
      ativo: true
    }
  },
  {
    $group: {
      _id: "$curso.nome",
      total_ativos: { $sum: 1 }
    }
  },
  { $sort: { total_ativos: -1 } }
]);
```

### **2️⃣ Departamento com mais professores**
```js
db.professores.aggregate([
  {
    $group: {
      _id: "$departamento",
      total_professores: { $sum: 1 }
    }
  },
  { $sort: { total_professores: -1 } },
  { $limit: 1 }
]);
```

### **3️⃣ Top-5 turmas por número de alunos**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "turmas",
      localField: "curso_id",
      foreignField: "curso_id",
      as: "turma"
    }
  },
  { $unwind: "$turma" },
  {
    $group: {
      _id: "$turma.codigo",
      total_alunos: { $sum: 1 }
    }
  },
  { $sort: { total_alunos: -1 } },
  { $limit: 5 }
]);
```

### **4️⃣ Cidades únicas com count**
```js
db.alunos.aggregate([
  {
    $group: {
      _id: "$endereco.cidade",
      total: { $sum: 1 }
    }
  },
  { $sort: { total: -1 } }
]);
```

---

## 🔵 Intermediário / Avançado

### **5️⃣ Ranking por retenção (ativos / total)**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "cursos",
      localField: "curso_id",
      foreignField: "_id",
      as: "curso"
    }
  },
  { $unwind: "$curso" },
  {
    $group: {
      _id: "$curso.nome",
      total_alunos: { $sum: 1 },
      ativos: { $sum: { $cond: ["$ativo", 1, 0] } }
    }
  },
  {
    $project: {
      _id: 1,
      total_alunos: 1,
      ativos: 1,
      taxa_retencao: {
        $cond: [
          { $eq: ["$total_alunos", 0] },
          0,
          { $divide: ["$ativos", "$total_alunos"] }
        ]
      }
    }
  },
  { $sort: { taxa_retencao: -1 } }
]);
```

### **6️⃣ Bolsistas em cursos de Medicina**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "cursos",
      localField: "curso_id",
      foreignField: "_id",
      as: "curso"
    }
  },
  { $unwind: "$curso" },
  {
    $match: {
      "curso.departamento": /medicina/i,
      bolsista: true
    }
  },
  {
    $project: {
      _id: 0,
      nome: 1,
      "curso.nome": 1,
      "curso.departamento": 1
    }
  }
]);
```

### **7️⃣ Professores com alunos de múltiplas cidades**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "cursos",
      localField: "curso_id",
      foreignField: "_id",
      as: "curso"
    }
  },
  { $unwind: "$curso" },
  {
    $lookup: {
      from: "professores",
      localField: "curso.departamento",
      foreignField: "departamento",
      as: "professor"
    }
  },
  { $unwind: "$professor" },
  {
    $group: {
      _id: "$professor.nome",
      cidades: { $addToSet: "$endereco.cidade" }
    }
  },
  {
    $addFields: {
      total_cidades: { $size: "$cidades" }
    }
  },
  { $match: { total_cidades: { $gt: 1 } } },
  { $sort: { total_cidades: -1 } }
]);
```

### **8️⃣ ROI por departamento (alunos_ativos / (professores * cursos))**
```js
db.alunos.aggregate([
  {
    $lookup: {
      from: "cursos",
      localField: "curso_id",
      foreignField: "_id",
      as: "curso"
    }
  },
  { $unwind: "$curso" },
  {
    $group: {
      _id: "$curso.departamento",
      alunos_ativos: { $sum: { $cond: ["$ativo", 1, 0] } },
      cursos: { $addToSet: "$curso._id" }
    }
  },
  {
    $lookup: {
      from: "professores",
      localField: "_id",
      foreignField: "departamento",
      as: "professores"
    }
  },
  {
    $addFields: {
      num_professores: { $size: "$professores" },
      num_cursos: { $size: "$cursos" },
      roi: {
        $cond: [
          { $eq: [{ $multiply: [{ $size: "$professores" }, { $size: "$cursos" }] }, 0] },
          0,
          {
            $divide: [
              "$alunos_ativos",
              { $multiply: [{ $size: "$professores" }, { $size: "$cursos" }] }
            ]
          }
        ]
      }
    }
  },
  {
    $project: {
      _id: 1,
      alunos_ativos: 1,
      num_professores: 1,
      num_cursos: 1,
      roi: 1
    }
  },
  { $sort: { roi: -1 } }
]);
```

---

**Autor:** Professor Diego Ramos Inácio  
**Disciplina:** Banco de Dados Não Relacional (MongoDB)  
**Universidade de Vassouras – Campus Saquarema**

