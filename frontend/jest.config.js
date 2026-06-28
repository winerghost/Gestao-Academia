// Configuração do Jest para o Next.js.
// `next/jest` injeta automaticamente: transformador SWC, aliases de path (jsconfig.json),
// mocks para arquivos estáticos (CSS, imagens) e variáveis de ambiente do Next.
const nextJest = require('next/jest')

const createJestConfig = nextJest({ dir: './' })

module.exports = createJestConfig({
  // Carrega os matchers do Testing Library (@testing-library/jest-dom)
  // antes de cada arquivo de teste.
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // jsdom simula o DOM do navegador — necessário para testar hooks React.
  testEnvironment: 'jest-environment-jsdom',

  // Convenção de arquivos de teste.
  testMatch: [
    '**/__tests__/**/*.{js,jsx,ts,tsx}',
    '**/*.test.{js,jsx,ts,tsx}',
  ],

  // Mapeia o alias @/ definido no jsconfig.json.
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
})
