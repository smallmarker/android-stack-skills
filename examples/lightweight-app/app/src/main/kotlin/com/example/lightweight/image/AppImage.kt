package com.example.lightweight.image

import android.content.Context
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil3.ImageLoader
import coil3.SingletonImageLoader
import coil3.compose.SubcomposeAsyncImage
import coil3.compose.SubcomposeAsyncImageContent
import coil3.disk.DiskCache
import coil3.memory.MemoryCache
import okio.Path.Companion.toOkioPath

object AppImages {
    /** Call once from Application.onCreate, before the first request. */
    fun initialize(context: Context) {
        SingletonImageLoader.setSafe { appContext ->
            ImageLoader.Builder(appContext)
                .memoryCache { MemoryCache.Builder().maxSizePercent(appContext, 0.20).build() }
                .diskCache {
                    DiskCache.Builder().directory(appContext.cacheDir.resolve("coil_images").toOkioPath())
                        .maxSizeBytes(64L * 1024 * 1024).build()
                }
                .build()
        }
    }
}

/** Pass CircleShape for avatars. Decorative images should use a null description. */
@Composable
fun AppImage(
    url: String?,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(8.dp),
    contentScale: ContentScale = ContentScale.Crop,
    placeholder: Painter? = null,
    error: Painter? = null,
    loading: @Composable (() -> Unit)? = null,
    failure: @Composable (() -> Unit)? = null,
) {
    SubcomposeAsyncImage(
        model = url,
        contentDescription = contentDescription,
        modifier = modifier.clip(shape),
        contentScale = contentScale,
        loading = {
            if (loading != null) loading() else if (placeholder != null) {
                SubcomposeAsyncImageContent(painter = placeholder)
            } else Box(Modifier)
        },
        error = {
            if (failure != null) failure() else if (error != null) {
                SubcomposeAsyncImageContent(painter = error)
            } else Box(Modifier)
        },
    )
}
