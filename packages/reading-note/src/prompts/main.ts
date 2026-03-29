export function buildMainPrompt(input: {
  text: string;
  history?: string[];
  feeling?: string | null;
  context?: string;
}) {
  const history = input.history && input.history.length > 0 ? input.history.join(" | ") : "无";
  const feeling = input.feeling ?? "无";
  const context = input.context?.trim() || "无";

  return [
    "TASK=reading_note",
    "LANGUAGE=zh-CN",
    `TEXT=${input.text.replace(/\s+/g, " ").trim()}`,
    `HISTORY=${history.replace(/\s+/g, " ").trim()}`,
    `FEELING=${String(feeling).replace(/\s+/g, " ").trim()}`,
    `CONTEXT=${context.replace(/\s+/g, " ").trim()}`,
    "INSTRUCTION=请按 HWP 协议持续展开，不要给最终答案；问题、变量、路径、张力尽量使用中文；重点围绕句子理解、关键观点、与历史记录的关联和可能的盲点。",
  ].join(" ; ");
}
