# Design: Sequenciador anti-plágio

## Contexto

O pipeline já gera `ClipSpec` individuais, mas a ordem de entrada pode colocar
clipes do mesmo vídeo lado a lado. Esta etapa implementa a TASK-025 para
intercalar fontes diferentes sempre que a distribuição permitir. O sequencer
não executa FFmpeg e não altera o conteúdo dos clipes.

## Objetivos

- Reordenar clipes para evitar fontes consecutivas.
- Priorizar grupos com mais clipes para reduzir sobras difíceis de intercalar.
- Preservar cada `ClipSpec` exatamente uma vez.
- Retornar `SequencedClip` com posições sequenciais.
- Falhar explicitamente quando a regra anti-plágio não puder ser satisfeita.

## Contrato

```python
def sequence_clips_anti_plagiarism(
    clips: list[ClipSpec],
) -> list[SequencedClip]:
    ...
```

- Lista vazia retorna `[]`.
- Uma única fonte gera `AntiPlagiarismError`, orientando o usuário a adicionar
  mais vídeos.
- Duas ou mais fontes são agrupadas por `source_video`.
- Se a distribuição não permitir evitar adjacência, a função gera
  `AntiPlagiarismError` em vez de retornar uma sequência inválida.

## Algoritmo

1. Agrupar os clipes por `source_video`, mantendo a ordem original dentro de
   cada grupo.
2. Inserir os grupos em um max-heap implementado com tamanhos negativos,
   juntamente com o identificador da fonte.
3. Retirar o grupo mais populoso cujo identificador seja diferente do último
   usado; retirar um clipe e reinserir o grupo se ainda houver itens.
4. Criar `SequencedClip` com `sequence_position` começando em zero.
5. Se não existir grupo elegível diferente da última fonte enquanto ainda há
   clipes, lançar `AntiPlagiarismError`.
6. Percorrer a saída e validar explicitamente que fontes adjacentes são
   diferentes. A validação usará `raise`, nunca `assert`.

## Tratamento de erros

- Entrada vazia não é erro.
- Uma única fonte gera erro de domínio com orientação acionável.
- Distribuição impossível gera o mesmo erro de domínio, informando que mais
  fontes ou uma distribuição diferente são necessárias.
- Nenhum erro será ocultado por fallback ou por uma sequência parcialmente
  válida.

## Testes

Os testes cobrirão:

- entrada vazia;
- uma única fonte;
- alternância perfeita entre dois grupos uniformes;
- distribuição uniforme entre várias fontes;
- preservação de todos os clipes e posições sequenciais;
- distribuição desbalanceada impossível;
- garantia de que não há adjacências iguais na saída válida.

## Fora do escopo

- Alterar velocidade ou aplicar efeitos nos clipes.
- Cortar ou recompor arquivos.
- Criar endpoints HTTP ou telas frontend.
