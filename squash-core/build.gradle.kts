plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.kotlinSerialization)
    alias(libs.plugins.androidLibrary)
    id("maven-publish")
    id("signing")
}

group = "io.github.ashwin-s-ashok"
version = "0.1.0"

kotlin {
    // JVM target
    jvm()

    // Android target
    androidTarget {
        compilations.all {
            kotlinOptions {
                jvmTarget = "17"
            }
        }
    }

    // iOS targets
    iosX64()
    iosArm64()
    iosSimulatorArm64()

    // JS target
    js(IR) {
        browser()
        nodejs()
        binaries.library()
    }

    sourceSets {
        commonMain.dependencies {
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.kotlinx.coroutines.core)
        }

        commonTest.dependencies {
            implementation(libs.kotlin.test)
            implementation(libs.kotlinx.coroutines.test)
        }

        androidMain.dependencies {
            implementation(libs.okhttp)
            implementation(libs.retrofit)
        }
    }
}

android {
    namespace = "com.squash.core"
    compileSdk = 35
    defaultConfig {
        minSdk = 24
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// Configures publishing for all targets (Android, iOS, JVM, JS)
publishing {
    publications.withType<MavenPublication> {
        val pubName = name
        val javadocTask = tasks.register("${pubName}JavadocJar", Jar::class) {
            archiveClassifier.set("javadoc")
            destinationDirectory.set(layout.buildDirectory.dir("libs/javadoc-${pubName}"))
        }
        artifact(javadocTask)
        
        pom {
            name.set("Squash Protocol")
            description.set("Hybrid JSON Compact Protocol — schema-aware transport optimization for JSON payloads")
            url.set("https://github.com/ASHWIN-S-ASHOK/squash-protocol")
            
            licenses {
                license {
                    name.set("MIT License")
                    url.set("https://opensource.org/licenses/MIT")
                }
            }
            developers {
                developer {
                    id.set("ashwin")
                    name.set("Ashwin")
                    email.set("ashwin.s.ashok@gmail.com")
                }
            }
            scm {
                connection.set("scm:git:github.com/ASHWIN-S-ASHOK/squash-protocol.git")
                developerConnection.set("scm:git:ssh://github.com/ASHWIN-S-ASHOK/squash-protocol.git")
                url.set("https://github.com/ASHWIN-S-ASHOK/squash-protocol/tree/main")
            }
        }
    }

    repositories {
        maven {
            name = "MavenCentral"
            val releasesRepoUrl = uri("https://s01.oss.sonatype.org/service/local/staging/deploy/maven2/")
            val snapshotsRepoUrl = uri("https://s01.oss.sonatype.org/content/repositories/snapshots/")
            url = if (version.toString().endsWith("SNAPSHOT")) snapshotsRepoUrl else releasesRepoUrl
            credentials {
                username = System.getenv("MAVEN_USERNAME")
                password = System.getenv("MAVEN_PASSWORD")
            }
        }
        maven {
            name = "LocalRepo" // For testing publishing locally
            url = uri(layout.buildDirectory.dir("repo"))
        }
    }
}

// Maven Central requires artifacts to be signed.
// You must set ORG_GRADLE_PROJECT_signingKey and ORG_GRADLE_PROJECT_signingPassword environment variables.
signing {
    useInMemoryPgpKeys(System.getenv("ORG_GRADLE_PROJECT_signingKey"), System.getenv("ORG_GRADLE_PROJECT_signingPassword"))
    sign(publishing.publications)
}
