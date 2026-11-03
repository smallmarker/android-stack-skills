package com.example.standard.di

import com.example.standard.data.DefaultHomeRepository
import com.example.standard.data.HomeRepository
import com.example.standard.network.NetworkConfig
import com.example.standard.network.TokenProvider
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides fun repository(impl: DefaultHomeRepository): HomeRepository = impl
    @Provides fun config(): NetworkConfig = NetworkConfig("https://example.com/")
    @Provides fun tokens(): TokenProvider = TokenProvider { null }
}
