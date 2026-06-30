import "./globals.css";
import { connection } from "next/server";

export const metadata = {
  title: "Portal do Aluno — Gestão Academia",
  description: "Acompanhe suas mensalidades e frequência",
};

export default async function RootLayout({ children }) {
  // CSP com nonce exige renderização DINÂMICA: o proxy.js gera um nonce novo por
  // requisição e o Next injeta esse nonce nos <script> só durante o SSR. Se a
  // página for pré-renderizada no build, o shell sai com nonce ausente/velho e o
  // navegador bloqueia TODOS os scripts (a página carrega "morta"). connection()
  // aguarda a requisição e opta toda a árvore por renderização por request, de
  // modo que o nonce do HTML sempre case com o do header. Ver frontend/proxy.js e
  // node_modules/next/dist/docs/01-app/02-guides/content-security-policy.md.
  await connection();
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
