import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

export default function CreatePost() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    author: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    if (!formData.title.trim() || !formData.content.trim() || !formData.author.trim()) {
      setError('모든 필드를 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMsg = '게시물 작성에 실패했습니다.';

        try {
          if (contentType?.includes('application/json')) {
            const data = await response.json();
            errorMsg = data.error || errorMsg;
          } else {
            const text = await response.text();
            console.error('API returned non-JSON response:', text);
            errorMsg = `서버 오류 (${response.status}): 관리자에게 문의하세요.`;
          }
        } catch (parseError) {
          console.error('Failed to parse error response:', parseError);
          errorMsg = `서버 오류 (${response.status})`;
        }
        throw new Error(errorMsg);
      }

      const newPost = await response.json();
      router.push(`/posts/${newPost.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">DemoBoard</h1>
              <p className="text-gray-600 mt-2">새 게시물 작성</p>
            </div>
            <Link href="/">
              <button className="text-indigo-600 hover:text-indigo-700 font-medium">
                ← 돌아가기
              </button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Author */}
            <div>
              <label className="block text-gray-700 font-bold mb-2">
                작성자
              </label>
              <input
                type="text"
                name="author"
                value={formData.author}
                onChange={handleChange}
                placeholder="작성자 이름을 입력하세요"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Title */}
            <div>
              <label className="block text-gray-700 font-bold mb-2">
                제목
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="게시물 제목을 입력하세요"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Content */}
            <div>
              <label className="block text-gray-700 font-bold mb-2">
                내용
              </label>
              <textarea
                name="content"
                value={formData.content}
                onChange={handleChange}
                placeholder="게시물 내용을 입력하세요"
                rows={10}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-4">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                {loading ? '작성 중...' : '게시물 작성'}
              </button>
              <Link href="/">
                <button
                  type="button"
                  className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                  취소
                </button>
              </Link>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
