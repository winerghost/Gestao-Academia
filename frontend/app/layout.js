import "./globals.css";

export const metadata = {
  title: "Portal do Aluno — Gestão Academia",
  description: "Acompanhe suas mensalidades e frequência",
};

export default function RootLayout({ children }) {
  return (
    // suppressHydrationWarning: extensões do navegador (ex.: ColorZilla, que
    // injeta cz-shortcut-listen) adicionam atributos em <html>/<body> antes do
    // React hidratar. Silencia só o mismatch deste nível — não esconde os reais
    // dentro da árvore.
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="bg-gray-50 text-gray-900 antialiased min-h-screen" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
