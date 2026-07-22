// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ImageGallery } from "./image-gallery";

describe("ImageGallery", () => {
  it("shows a placeholder when there are no ready images", () => {
    render(
      <ImageGallery
        title="Bridal Special"
        images={[
          {
            id: "i1",
            design_id: "d1",
            status: "processing",
            image_url: null,
            thumbnail_small_url: null,
            thumbnail_medium_url: null,
            width: null,
            height: null,
            sort_order: 0,
            is_primary: true,
            processing_error: null,
          },
        ]}
      />,
    );

    expect(screen.getByText("Image coming soon")).toBeInTheDocument();
  });

  it("renders the primary image and a thumbnail strip for multiple ready images", () => {
    const images = [
      {
        id: "i1",
        design_id: "d1",
        status: "ready",
        image_url: "/full-1.jpg",
        thumbnail_small_url: "/small-1.jpg",
        thumbnail_medium_url: "/medium-1.jpg",
        width: 800,
        height: 800,
        sort_order: 0,
        is_primary: true,
        processing_error: null,
      },
      {
        id: "i2",
        design_id: "d1",
        status: "ready",
        image_url: "/full-2.jpg",
        thumbnail_small_url: "/small-2.jpg",
        thumbnail_medium_url: "/medium-2.jpg",
        width: 800,
        height: 800,
        sort_order: 1,
        is_primary: false,
        processing_error: null,
      },
    ];

    render(<ImageGallery title="Bridal Special" images={images} />);

    expect(screen.getByAltText("Bridal Special mehndi design, image 1 of 2")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "More images" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("omits the thumbnail strip when there is only one ready image", () => {
    render(
      <ImageGallery
        title="Bridal Special"
        images={[
          {
            id: "i1",
            design_id: "d1",
            status: "ready",
            image_url: "/full-1.jpg",
            thumbnail_small_url: null,
            thumbnail_medium_url: "/medium-1.jpg",
            width: 800,
            height: 800,
            sort_order: 0,
            is_primary: true,
            processing_error: null,
          },
        ]}
      />,
    );

    expect(screen.queryByRole("list", { name: "More images" })).not.toBeInTheDocument();
  });
});
