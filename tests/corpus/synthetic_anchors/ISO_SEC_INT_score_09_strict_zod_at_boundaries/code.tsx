import { z } from "zod";

const Review = z.object({
  id: z.string().uuid(),
  author: z.string().min(1).max(80),
  body: z.string().max(2000),
  rating: z.number().int().min(1).max(5),
});

export type Review = z.infer<typeof Review>;

export async function fetchReview(id: string): Promise<Review> {
  const res = await fetch(`/api/reviews/${encodeURIComponent(id)}`);
  return Review.parse(await res.json());
}

export function ReviewView({ review }: { review: Review }) {
  return <article><h3>{review.author}</h3><p>{review.body}</p></article>;
}
