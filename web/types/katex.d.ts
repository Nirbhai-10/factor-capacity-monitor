declare module "katex" {
  export function render(
    tex: string,
    element: HTMLElement,
    options?: { throwOnError?: boolean; displayMode?: boolean; output?: string }
  ): void;
  const _default: { render: typeof render };
  export default _default;
}
