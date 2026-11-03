package com.example.standard.network

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import retrofit2.Retrofit

/** App supplies NetworkConfig and TokenProvider bindings (see Usage.md). */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton
    fun retrofit(config: NetworkConfig, tokens: TokenProvider): Retrofit =
        HttpClientFactory.retrofit(config, tokens)

    @Provides
    fun userApi(retrofit: Retrofit): UserApi = retrofit.create(UserApi::class.java)
}
