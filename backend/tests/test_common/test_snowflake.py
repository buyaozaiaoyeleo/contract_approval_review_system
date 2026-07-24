"""雪花 ID 生成器单元测试"""


from app.common.snowflake import generate_id, init_snowflake


class TestSnowflake:
    """雪花 ID 生成器测试"""

    def test_init_snowflake(self):
        """测试初始化雪花算法"""
        init_snowflake(worker_id=1, datacenter_id=1)
        # 验证初始化不抛异常

    def test_generate_id_unique(self):
        """测试生成的 ID 唯一性"""
        init_snowflake(worker_id=1, datacenter_id=1)

        ids = [generate_id() for _ in range(1000)]
        assert len(ids) == len(set(ids)), "生成的 ID 应该唯一"

    def test_generate_id_positive(self):
        """测试生成的 ID 是正整数"""
        init_snowflake(worker_id=1, datacenter_id=1)

        for _ in range(100):
            assert generate_id() > 0

    def test_generate_id_ordering(self):
        """测试 ID 按时间递增"""
        init_snowflake(worker_id=1, datacenter_id=1)

        ids = [generate_id() for _ in range(100)]
        assert ids == sorted(ids), "ID 应该按时间递增"

    def test_different_worker_produce_different_ids(self):
        """测试不同 Worker 产生的 ID 不同"""
        worker_1_ids = []
        worker_2_ids = []

        init_snowflake(worker_id=1, datacenter_id=1)
        for _ in range(50):
            worker_1_ids.append(generate_id())

        init_snowflake(worker_id=2, datacenter_id=1)
        for _ in range(50):
            worker_2_ids.append(generate_id())

        # 两个 Worker 的 ID 集合不应有交集
        assert not set(worker_1_ids) & set(worker_2_ids)
