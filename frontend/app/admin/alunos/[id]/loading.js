import { AlunoDetalheSkeleton } from './_skeleton'

// Exibido pelo Next.js App Router imediatamente ao iniciar a navegação,
// antes mesmo do componente page.js montar — elimina o "branco" entre clique e load.
export default function Loading() {
  return <AlunoDetalheSkeleton />
}
