"use client";

import Image from "next/image";
import { useState } from "react";

import type { Product } from "@/lib/api";

/** The main photo, with thumbnails to switch between a product's photos. */
export function ProductGallery({ product }: { product: Product }) {
  const [index, setIndex] = useState(0);
  const photos = product.photos;
  const main = photos[index]?.url ?? product.photo_url;
  if (!main) return null;

  return (
    <div className="flex flex-col border-b border-zinc-100 bg-white dark:border-zinc-800">
      <Image
        src={main}
        alt={photos.length > 1 ? `${product.name}, photo ${index + 1} of ${photos.length}` : product.name}
        width={400}
        height={400}
        unoptimized
        className="aspect-square w-full object-contain p-3 transition-transform duration-300 group-hover:scale-[1.02]"
        data-testid={`product-photo-${product.sku}`}
      />
      {photos.length > 1 ? (
        <div className="flex justify-center gap-2 border-t border-zinc-100 bg-zinc-50/60 p-2 dark:border-zinc-800 dark:bg-zinc-900" role="group" aria-label={`${product.name} photos`}>
          {photos.map((photo, i) => (
            <button
              key={photo.id}
              type="button"
              onClick={() => setIndex(i)}
              aria-label={`Show photo ${i + 1}`}
              aria-pressed={i === index}
              className={`overflow-hidden rounded-lg border-2 bg-white transition ${i === index ? "border-indigo-500" : "border-transparent opacity-70 hover:opacity-100"}`}
            >
              <Image src={photo.url} alt="" width={48} height={48} unoptimized className="h-12 w-12 object-contain" />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
