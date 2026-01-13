export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Reverse Muse
        </h1>
        <p className="text-lg text-gray-600">
          AI-Powered Reading Companion
        </p>
        <div className="mt-8 space-y-4">
          <a
            href="/reading"
            className="block px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            开始阅读
          </a>
          <a
            href="/api/health"
            className="block text-gray-600 hover:text-gray-900"
          >
            API 健康检查
          </a>
        </div>
      </div>
    </div>
  );
}
