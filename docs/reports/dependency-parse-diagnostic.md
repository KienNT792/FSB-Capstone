# Dependency Parse Diagnostic

Classifies `dependency_parse_failed=1` rows into worktree/file-availability issues versus `javalang` parser exceptions. Historical checks use `GIT_NO_LAZY_FETCH=1` so blobless clones do not silently fetch missing blobs.

| Repo | Rows | Failed rows | Failed rate | Failed unique tests | Total unique tests |
| --- | --- | --- | --- | --- | --- |
| adamfisk@LittleProxy | 15772 | 930 | 5.9% | 12 | 52 |
| deeplearning4j@deeplearning4j | 15509 | 15171 | 97.8% | 167 | 174 |
| l0rdn1kk0n@wicket-bootstrap | 48228 | 6200 | 12.9% | 44 | 97 |
| neuland@jade4j | 35887 | 10981 | 30.6% | 16 | 46 |
| thinkaurelius@titan | 45058 | 29424 | 65.3% | 96 | 121 |

| Repo | Category | Failed rows | Share of failed | Unique tests |
| --- | --- | --- | --- | --- |
| adamfisk@LittleProxy | worktree_file_missing | 930 | 100.0% | 12 |
| deeplearning4j@deeplearning4j | worktree_file_missing | 15171 | 100.0% | 167 |
| l0rdn1kk0n@wicket-bootstrap | worktree_file_missing | 6200 | 100.0% | 44 |
| neuland@jade4j | worktree_file_missing | 10981 | 100.0% | 16 |
| thinkaurelius@titan | worktree_file_missing | 29424 | 100.0% | 96 |

## Worktree Examples

### adamfisk@LittleProxy / worktree_file_missing
| Test id | Expected path | Located path | Detail |
| --- | --- | --- | --- |
| org.littleshoot.proxy.DefaultProxyCacheManagerTest | src/test/java/org/littleshoot/proxy/DefaultProxyCacheManagerTest.java | data/git-repos/adamfisk@LittleProxy/src/test/java/org/littleshoot/proxy/DefaultProxyCacheManagerTest.java | No matching test source found in current checkout. |
| org.littleshoot.proxy.HttpProxyTest | src/test/java/org/littleshoot/proxy/HttpProxyTest.java | data/git-repos/adamfisk@LittleProxy/src/test/java/org/littleshoot/proxy/HttpProxyTest.java | No matching test source found in current checkout. |
| org.littleshoot.proxy.HttpRequestPathMatcherTest | src/test/java/org/littleshoot/proxy/HttpRequestPathMatcherTest.java | data/git-repos/adamfisk@LittleProxy/src/test/java/org/littleshoot/proxy/HttpRequestPathMatcherTest.java | No matching test source found in current checkout. |
| org.littleshoot.proxy.ProxyChainTest | src/test/java/org/littleshoot/proxy/ProxyChainTest.java | data/git-repos/adamfisk@LittleProxy/src/test/java/org/littleshoot/proxy/ProxyChainTest.java | No matching test source found in current checkout. |
| org.littleshoot.proxy.ProxyUtilsTest | src/test/java/org/littleshoot/proxy/ProxyUtilsTest.java | data/git-repos/adamfisk@LittleProxy/src/test/java/org/littleshoot/proxy/ProxyUtilsTest.java | No matching test source found in current checkout. |

### deeplearning4j@deeplearning4j / worktree_file_missing
| Test id | Expected path | Located path | Detail |
| --- | --- | --- | --- |
| org.deeplearning4j.distributions.DistributionsTest | src/test/java/org/deeplearning4j/distributions/DistributionsTest.java | data/git-repos/deeplearning4j@deeplearning4j/src/test/java/org/deeplearning4j/distributions/DistributionsTest.java | No matching test source found in current checkout. |
| org.deeplearning4j.nn.HiddenLayerTest | src/test/java/org/deeplearning4j/nn/HiddenLayerTest.java | data/git-repos/deeplearning4j@deeplearning4j/src/test/java/org/deeplearning4j/nn/HiddenLayerTest.java | No matching test source found in current checkout. |
| org.deeplearning4j.nn.LogisticTest | src/test/java/org/deeplearning4j/nn/LogisticTest.java | data/git-repos/deeplearning4j@deeplearning4j/src/test/java/org/deeplearning4j/nn/LogisticTest.java | No matching test source found in current checkout. |
| org.deeplearning4j.nn.learning.AdaGradTest | src/test/java/org/deeplearning4j/nn/learning/AdaGradTest.java | data/git-repos/deeplearning4j@deeplearning4j/src/test/java/org/deeplearning4j/nn/learning/AdaGradTest.java | No matching test source found in current checkout. |
| org.deeplearning4j.autoencoder.DeepAutoEncoderTest | src/test/java/org/deeplearning4j/autoencoder/DeepAutoEncoderTest.java | data/git-repos/deeplearning4j@deeplearning4j/src/test/java/org/deeplearning4j/autoencoder/DeepAutoEncoderTest.java | No matching test source found in current checkout. |

### l0rdn1kk0n@wicket-bootstrap / worktree_file_missing
| Test id | Expected path | Located path | Detail |
| --- | --- | --- | --- |
| de.agilecoders.wicket.core.markup.html.bootstrap.block.BadgeBehaviorTest | src/test/java/de/agilecoders/wicket/core/markup/html/bootstrap/block/BadgeBehaviorTest.java | data/git-repos/l0rdn1kk0n@wicket-bootstrap/src/test/java/de/agilecoders/wicket/core/markup/html/bootstrap/block/BadgeBehaviorTest.java | No matching test source found in current checkout. |
| de.agilecoders.wicket.core.markup.html.bootstrap.form.TypeaheadTest | src/test/java/de/agilecoders/wicket/core/markup/html/bootstrap/form/TypeaheadTest.java | data/git-repos/l0rdn1kk0n@wicket-bootstrap/src/test/java/de/agilecoders/wicket/core/markup/html/bootstrap/form/TypeaheadTest.java | No matching test source found in current checkout. |
| de.agilecoders.wicket.core.util.JQueryTest | src/test/java/de/agilecoders/wicket/core/util/JQueryTest.java | data/git-repos/l0rdn1kk0n@wicket-bootstrap/src/test/java/de/agilecoders/wicket/core/util/JQueryTest.java | No matching test source found in current checkout. |
| de.agilecoders.wicket.core.util.JsonTest | src/test/java/de/agilecoders/wicket/core/util/JsonTest.java | data/git-repos/l0rdn1kk0n@wicket-bootstrap/src/test/java/de/agilecoders/wicket/core/util/JsonTest.java | No matching test source found in current checkout. |
| de.agilecoders.wicket.less.Less4JCompilerTest | src/test/java/de/agilecoders/wicket/less/Less4JCompilerTest.java | data/git-repos/l0rdn1kk0n@wicket-bootstrap/src/test/java/de/agilecoders/wicket/less/Less4JCompilerTest.java | No matching test source found in current checkout. |

### neuland@jade4j / worktree_file_missing
| Test id | Expected path | Located path | Detail |
| --- | --- | --- | --- |
| de.neuland.jade4j.lexer.JadeLexerTest | src/test/java/de/neuland/jade4j/lexer/JadeLexerTest.java | data/git-repos/neuland@jade4j/src/test/java/de/neuland/jade4j/lexer/JadeLexerTest.java | No matching test source found in current checkout. |
| de.neuland.jade4j.lexer.LexerTest | src/test/java/de/neuland/jade4j/lexer/LexerTest.java | data/git-repos/neuland@jade4j/src/test/java/de/neuland/jade4j/lexer/LexerTest.java | No matching test source found in current checkout. |
| de.neuland.jade4j.lexer.WorkTest | src/test/java/de/neuland/jade4j/lexer/WorkTest.java | data/git-repos/neuland@jade4j/src/test/java/de/neuland/jade4j/lexer/WorkTest.java | No matching test source found in current checkout. |
| de.neuland.jade4j.lexer.token.AttributeTest | src/test/java/de/neuland/jade4j/lexer/token/AttributeTest.java | data/git-repos/neuland@jade4j/src/test/java/de/neuland/jade4j/lexer/token/AttributeTest.java | No matching test source found in current checkout. |
| de.neuland.jade4j.lexer.token.CommentTest | src/test/java/de/neuland/jade4j/lexer/token/CommentTest.java | data/git-repos/neuland@jade4j/src/test/java/de/neuland/jade4j/lexer/token/CommentTest.java | No matching test source found in current checkout. |

### thinkaurelius@titan / worktree_file_missing
| Test id | Expected path | Located path | Detail |
| --- | --- | --- | --- |
| com.thinkaurelius.titan.blueprints.InMemoryBlueprintsTest | src/test/java/com/thinkaurelius/titan/blueprints/InMemoryBlueprintsTest.java | data/git-repos/thinkaurelius@titan/src/test/java/com/thinkaurelius/titan/blueprints/InMemoryBlueprintsTest.java | No matching test source found in current checkout. |
| com.thinkaurelius.titan.blueprints.LocalBlueprintsTest | src/test/java/com/thinkaurelius/titan/blueprints/LocalBlueprintsTest.java | data/git-repos/thinkaurelius@titan/src/test/java/com/thinkaurelius/titan/blueprints/LocalBlueprintsTest.java | No matching test source found in current checkout. |
| com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyDBjeKeyColumnValueTest | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueTest.java | data/git-repos/thinkaurelius@titan/src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueTest.java | No matching test source found in current checkout. |
| com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyDBjeKeyColumnValueVariableTest | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueVariableTest.java | data/git-repos/thinkaurelius@titan/src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueVariableTest.java | No matching test source found in current checkout. |
| com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyJEKeyValueTest | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyJEKeyValueTest.java | data/git-repos/thinkaurelius@titan/src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyJEKeyValueTest.java | No matching test source found in current checkout. |

## Historical Commit Samples
| Repo | Commit | Test id | Tree status | Candidates | Blob status | Parse status | Detail |
| --- | --- | --- | --- | --- | --- | --- | --- |
| adamfisk@LittleProxy | eb60eb6603d2 | org.littleshoot.proxy.HttpProxyTest | candidate_found | src/test/java/org/littleshoot/proxy/HttpProxyTest.java | blob_available | javalang_parse_ok |  |
| adamfisk@LittleProxy | 231df0bface5 | org.littleshoot.proxy.DefaultProxyCacheManagerTest | candidate_found | src/test/java/org/littleshoot/proxy/DefaultProxyCacheManagerTest.java | blob_available | javalang_parse_ok |  |
| adamfisk@LittleProxy | 231df0bface5 | org.littleshoot.proxy.HttpProxyTest | candidate_found | src/test/java/org/littleshoot/proxy/HttpProxyTest.java | blob_available | javalang_parse_ok |  |
| adamfisk@LittleProxy | 231df0bface5 | org.littleshoot.proxy.HttpRequestPathMatcherTest | candidate_found | src/test/java/org/littleshoot/proxy/HttpRequestPathMatcherTest.java | blob_available | javalang_parse_ok |  |
| adamfisk@LittleProxy | 231df0bface5 | org.littleshoot.proxy.ProxyChainTest | candidate_found | src/test/java/org/littleshoot/proxy/ProxyChainTest.java | blob_available | javalang_parse_ok |  |
| deeplearning4j@deeplearning4j | 2f2c59e8394a | com.ccc.deeplearning.dbn.matrix.jblas.DBNTest | candidate_found | deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/dbn/matrix/jblas/DBNTest.java<br>deeplearning4j-parent/deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/dbn/matrix/jblas/DBNTest.java | blob_missing_or_lazy_fetch_required;blob_missing_or_lazy_fetch_required | not_checked;not_checked |  |
| deeplearning4j@deeplearning4j | 2f2c59e8394a | com.ccc.deeplearning.datasets.fetchers.IrisFetcherTest | candidate_found | deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/fetchers/IrisFetcherTest.java<br>deeplearning4j-parent/deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/fetchers/IrisFetcherTest.java | blob_missing_or_lazy_fetch_required;blob_missing_or_lazy_fetch_required | not_checked;not_checked |  |
| deeplearning4j@deeplearning4j | 2f2c59e8394a | com.ccc.deeplearning.datasets.fetchers.MnistFetcherTest | candidate_found | deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/fetchers/MnistFetcherTest.java<br>deeplearning4j-parent/deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/fetchers/MnistFetcherTest.java | blob_missing_or_lazy_fetch_required;blob_missing_or_lazy_fetch_required | not_checked;not_checked |  |
| deeplearning4j@deeplearning4j | 2f2c59e8394a | com.ccc.deeplearning.datasets.iterator.impl.IrisDataSetIteratorTest | candidate_found | deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/iterator/impl/IrisDataSetIteratorTest.java<br>deeplearning4j-parent/deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/iterator/impl/IrisDataSetIteratorTest.java | blob_missing_or_lazy_fetch_required;blob_missing_or_lazy_fetch_required | not_checked;not_checked |  |
| deeplearning4j@deeplearning4j | 2f2c59e8394a | com.ccc.deeplearning.datasets.iterator.impl.MnistDataSetIteratorTest | candidate_found | deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/iterator/impl/MnistDataSetIteratorTest.java<br>deeplearning4j-parent/deeplearning4j-parent/deeplearning4j-core/src/test/java/com/ccc/deeplearning/datasets/iterator/impl/MnistDataSetIteratorTest.java | blob_missing_or_lazy_fetch_required;blob_missing_or_lazy_fetch_required | not_checked;not_checked |  |
| l0rdn1kk0n@wicket-bootstrap | 431c50083212 | de.agilecoders.wicket.core.markup.html.bootstrap.block.BadgeBehaviorTest | tree_unavailable |  | not_checked | not_checked | fatal: not a tree object |
| l0rdn1kk0n@wicket-bootstrap | 431c50083212 | de.agilecoders.wicket.core.markup.html.bootstrap.form.TypeaheadTest | tree_unavailable |  | not_checked | not_checked | fatal: not a tree object |
| l0rdn1kk0n@wicket-bootstrap | 431c50083212 | de.agilecoders.wicket.core.util.JQueryTest | tree_unavailable |  | not_checked | not_checked | fatal: not a tree object |
| l0rdn1kk0n@wicket-bootstrap | 431c50083212 | de.agilecoders.wicket.core.util.JsonTest | tree_unavailable |  | not_checked | not_checked | fatal: not a tree object |
| l0rdn1kk0n@wicket-bootstrap | 431c50083212 | de.agilecoders.wicket.less.LessResourceTest | tree_unavailable |  | not_checked | not_checked | fatal: not a tree object |
| neuland@jade4j | 75e77f6a93b4 | de.neuland.jade4j.lexer.JadeLexerTest | candidate_found | src/test/java/de/neuland/jade4j/lexer/JadeLexerTest.java | blob_available | javalang_parse_ok |  |
| neuland@jade4j | 75e77f6a93b4 | de.neuland.jade4j.lexer.LexerTest | candidate_found | src/test/java/de/neuland/jade4j/lexer/LexerTest.java | blob_available | javalang_parse_ok |  |
| neuland@jade4j | 75e77f6a93b4 | de.neuland.jade4j.lexer.WorkTest | candidate_found | src/test/java/de/neuland/jade4j/lexer/WorkTest.java | blob_available | javalang_parse_ok |  |
| neuland@jade4j | 75e77f6a93b4 | de.neuland.jade4j.lexer.token.AttributeTest | candidate_found | src/test/java/de/neuland/jade4j/lexer/token/AttributeTest.java | blob_available | javalang_parse_ok |  |
| neuland@jade4j | 75e77f6a93b4 | de.neuland.jade4j.lexer.token.CommentTest | candidate_found | src/test/java/de/neuland/jade4j/lexer/token/CommentTest.java | blob_available | javalang_parse_ok |  |
| thinkaurelius@titan | f794ac462ae5 | com.thinkaurelius.titan.blueprints.InMemoryBlueprintsTest | candidate_found | src/test/java/com/thinkaurelius/titan/blueprints/InMemoryBlueprintsTest.java | blob_available | javalang_parse_ok |  |
| thinkaurelius@titan | f794ac462ae5 | com.thinkaurelius.titan.blueprints.LocalBlueprintsTest | candidate_found | src/test/java/com/thinkaurelius/titan/blueprints/LocalBlueprintsTest.java | blob_available | javalang_parse_ok |  |
| thinkaurelius@titan | f794ac462ae5 | com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyDBjeKeyColumnValueTest | candidate_found | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueTest.java | blob_available | javalang_parse_ok |  |
| thinkaurelius@titan | f794ac462ae5 | com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyDBjeKeyColumnValueVariableTest | candidate_found | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyDBjeKeyColumnValueVariableTest.java | blob_available | javalang_parse_ok |  |
| thinkaurelius@titan | f794ac462ae5 | com.thinkaurelius.titan.diskstorage.berkeleyje.BerkeleyJEKeyValueTest | candidate_found | src/test/java/com/thinkaurelius/titan/diskstorage/berkeleyje/BerkeleyJEKeyValueTest.java | blob_available | javalang_parse_ok |  |

## Interpretation Guide

- `worktree_file_missing`: the current extractor cannot locate the test source in the checked-out repo snapshot. This can be a checkout/history issue or a test-id-to-path mismatch, but it is not a `javalang` syntax failure.
- `candidate_found` plus `blob_available`: the historical commit contains a matching test file and the local clone can read it without lazy fetch.
- `candidate_found` plus `blob_missing_or_lazy_fetch_required`: the historical commit tree names the file, but the local clone lacks the blob locally.
- `javalang_parse_exception`: the file exists/read succeeds, so parser replacement or fallback parsing is the relevant fix.
