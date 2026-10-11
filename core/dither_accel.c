#include <stdlib.h>
#include <stdint.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

EXPORT void atkinson_dither(double *pixels, int width, int height) {
    for (int y = 0; y < height; y++) {
        int y_offset = y * width;
        int y1_offset = (y + 1) * width;
        int y2_offset = (y + 2) * width;
        int has_y1 = (y + 1 < height);
        int has_y2 = (y + 2 < height);

        for (int x = 0; x < width; x++) {
            double old_val = pixels[y_offset + x];
            double new_val = (old_val >= 128.0) ? 255.0 : 0.0;
            pixels[y_offset + x] = new_val;
            double error = old_val - new_val;
            double e8 = error / 8.0;

            if (x + 1 < width) {
                pixels[y_offset + x + 1] += e8;
            }
            if (x + 2 < width) {
                pixels[y_offset + x + 2] += e8;
            }
            if (has_y1) {
                if (x - 1 >= 0) {
                    pixels[y1_offset + x - 1] += e8;
                }
                pixels[y1_offset + x] += e8;
                if (x + 1 < width) {
                    pixels[y1_offset + x + 1] += e8;
                }
            }
            if (has_y2) {
                pixels[y2_offset + x] += e8;
            }
        }
    }
}

EXPORT void jarvis_dither(double *pixels, int width, int height) {
    const double inv48 = 1.0 / 48.0;
    for (int y = 0; y < height; y++) {
        int y_offset = y * width;
        int y1_offset = (y + 1) * width;
        int y2_offset = (y + 2) * width;
        int has_y1 = (y + 1 < height);
        int has_y2 = (y + 2 < height);

        for (int x = 0; x < width; x++) {
            double old_val = pixels[y_offset + x];
            double new_val = (old_val >= 128.0) ? 255.0 : 0.0;
            pixels[y_offset + x] = new_val;
            double error = old_val - new_val;
            double e48 = error * inv48;

            if (x + 1 < width) {
                pixels[y_offset + x + 1] += e48 * 7.0;
            }
            if (x + 2 < width) {
                pixels[y_offset + x + 2] += e48 * 5.0;
            }
            if (has_y1) {
                if (x - 2 >= 0) {
                    pixels[y1_offset + x - 2] += e48 * 3.0;
                }
                if (x - 1 >= 0) {
                    pixels[y1_offset + x - 1] += e48 * 5.0;
                }
                pixels[y1_offset + x] += e48 * 7.0;
                if (x + 1 < width) {
                    pixels[y1_offset + x + 1] += e48 * 5.0;
                }
                if (x + 2 < width) {
                    pixels[y1_offset + x + 2] += e48 * 3.0;
                }
            }
            if (has_y2) {
                if (x - 2 >= 0) {
                    pixels[y2_offset + x - 2] += e48 * 1.0;
                }
                if (x - 1 >= 0) {
                    pixels[y2_offset + x - 1] += e48 * 3.0;
                }
                pixels[y2_offset + x] += e48 * 5.0;
                if (x + 1 < width) {
                    pixels[y2_offset + x + 1] += e48 * 3.0;
                }
                if (x + 2 < width) {
                    pixels[y2_offset + x + 2] += e48 * 1.0;
                }
            }
        }
    }
}
