import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 text-center">
      <p className="text-6xl font-bold text-gray-200">404</p>
      <h1 className="mt-4 text-xl font-semibold text-gray-900">Página no encontrada</h1>
      <p className="mt-2 text-sm text-gray-500">
        La página que buscas no existe o fue movida.
      </p>
      <Link
        href="/dashboard"
        className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Volver al dashboard
      </Link>
    </div>
  );
}
