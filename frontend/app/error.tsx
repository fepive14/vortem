'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 text-center">
      <p className="text-5xl font-bold text-gray-200">!</p>
      <h1 className="mt-4 text-xl font-semibold text-gray-900">Algo salió mal</h1>
      <p className="mt-2 text-sm text-gray-500">
        Ocurrió un error inesperado. Por favor, intenta de nuevo.
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Reintentar
      </button>
    </div>
  );
}
