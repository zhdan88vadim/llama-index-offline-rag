from llama_index.core import PromptTemplate

NO_INFO_PHRASE = "В документах нет информации"

QA_PROMPT_TEMPLATE = PromptTemplate(
    "Ты — ассистент по внутренним политикам. Используй ТОЛЬКО информацию из контекста.\n"
    "Если в контексте есть прямой ответ — дай его. Если ответа действительно нет — "
    "напиши '{no_info_phrase}'.\n\n"
    "Контекст:\n{context_str}\n\nВопрос: {query_str}\nОтвет:"
)

QA_PROMPT = QA_PROMPT_TEMPLATE.partial_format(no_info_phrase=NO_INFO_PHRASE)
