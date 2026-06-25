import "./globals.css";

export const metadata = {
  title: "Portal do Aluno — Gestão Academia",
  description: "Acompanhe suas mensalidades e frequência",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-50 text-gray-900 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
