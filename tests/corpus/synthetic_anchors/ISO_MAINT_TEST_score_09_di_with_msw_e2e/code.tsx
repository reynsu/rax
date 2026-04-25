type PostsApi = { listPosts(): Promise<{ id: string; title: string }[]> };

export function Home({ api }: { api: PostsApi }) {
  const [posts, setPosts] = useState<{ id: string; title: string }[]>([]);
  useEffect(() => { api.listPosts().then(setPosts); }, [api]);
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>;
}

// In tests, pass a stub `api`. In E2E (Playwright + MSW), intercept HTTP.
