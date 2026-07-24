<template>
  <div class="rule-edit-page">
    <PageHeader :title="isCreate ? '创建风险规则' : '编辑风险规则'" subtitle="配置风险审查规则的参数和条件" />

    <a-card :bordered="false" class="form-card">
      <a-spin :spinning="detailLoading">
        <a-form
          ref="formRef"
          :model="formState"
          :rules="rules"
          :label-col="{ span: 4 }"
          :wrapper-col="{ span: 16 }"
          @finish="handleSubmit"
        >
          <!-- 基本信息 -->
          <a-divider orientation="left">基本信息</a-divider>

          <a-form-item label="规则编码" name="rule_code">
            <a-input
              v-model:value="formState.rule_code"
              placeholder="如: AMOUNT_MIN_CHECK"
              :maxlength="64"
              :disabled="!isCreate"
            />
          </a-form-item>

          <a-form-item label="规则名称" name="rule_name">
            <a-input
              v-model:value="formState.rule_name"
              placeholder="如: 合同金额最小值检查"
              :maxlength="200"
            />
          </a-form-item>

          <a-form-item label="规则分类" name="rule_category">
            <a-select v-model:value="formState.rule_category" placeholder="选择规则分类">
              <a-select-option value="amount">金额类</a-select-option>
              <a-select-option value="term">期限类</a-select-option>
              <a-select-option value="clause">条款类</a-select-option>
              <a-select-option value="subject">主体类</a-select-option>
              <a-select-option value="compliance">合规类</a-select-option>
            </a-select>
          </a-form-item>

          <a-form-item label="规则类型" name="rule_type">
            <a-select v-model:value="formState.rule_type" placeholder="选择规则类型">
              <a-select-option value="field">字段匹配</a-select-option>
              <a-select-option value="llm">LLM语义</a-select-option>
              <a-select-option value="composite">组合规则</a-select-option>
            </a-select>
          </a-form-item>

          <!-- 风险配置 -->
          <a-divider orientation="left">风险配置</a-divider>

          <a-form-item label="风险等级" name="risk_level">
            <a-radio-group v-model:value="formState.risk_level">
              <a-radio-button value="HIGH">高风险</a-radio-button>
              <a-radio-button value="MEDIUM">中风险</a-radio-button>
              <a-radio-button value="LOW">低风险</a-radio-button>
            </a-radio-group>
          </a-form-item>

          <a-form-item label="优先级" name="priority">
            <a-input-number
              v-model:value="formState.priority"
              :min="0"
              :max="100"
              placeholder="数字越大优先级越高"
              style="width: 200px"
            />
          </a-form-item>

          <a-form-item label="规则配置" name="rule_config_json">
            <a-textarea
              v-model:value="formState.rule_config_json"
              placeholder='JSON 配置，如: {"field_name": "amount", "min_value": 1000}'
              :rows="6"
              :auto-size="{ minRows: 4, maxRows: 12 }"
            />
          </a-form-item>

          <a-form-item label="规则描述" name="description">
            <a-textarea
              v-model:value="formState.description"
              placeholder="描述规则的用途和检查逻辑"
              :rows="3"
              :maxlength="500"
              show-count
            />
          </a-form-item>

          <a-form-item label="启用状态" v-if="!isCreate">
            <a-switch v-model:checked="formState.is_enabled" />
          </a-form-item>

          <!-- 操作按钮 -->
          <a-form-item :wrapper-col="{ offset: 4, span: 16 }">
            <a-space>
              <a-button type="primary" html-type="submit" :loading="submitting">
                {{ isCreate ? '创建' : '保存' }}
              </a-button>
              <a-button @click="router.back()">取消</a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import type { FormInstance, Rule } from 'ant-design-vue/es/form'
import PageHeader from '@/components/common/PageHeader.vue'
import { createRiskRule, updateRiskRule, getRiskRules } from '@/api/rule'
import type { CreateRuleRequest, UpdateRuleRequest } from '@/types/rule'

const router = useRouter()
const route = useRoute()
const ruleId = route.params.id as string

const isCreate = computed(() => ruleId === 'new')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const detailLoading = ref(false)

// 表单状态
const formState = reactive<CreateRuleRequest & { is_enabled?: boolean }>({
  rule_code: '',
  rule_name: '',
  rule_category: '',
  rule_type: 'field',
  rule_config_json: null,
  priority: 0,
  risk_level: 'MEDIUM',
  description: null,
  is_enabled: true,
})

// 表单校验规则
const rules: Record<string, Rule[]> = {
  rule_code: [
    { required: true, message: '请输入规则编码', trigger: 'blur' },
    { pattern: /^[A-Z][A-Z0-9_]*$/, message: '编码格式: 大写字母开头，仅含大写字母/数字/下划线', trigger: 'blur' },
  ],
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_category: [{ required: true, message: '请选择规则分类', trigger: 'change' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  risk_level: [{ required: true, message: '请选择风险等级', trigger: 'change' }],
}

// 加载已有规则详情（编辑模式）
async function loadDetail() {
  if (isCreate.value) return

  detailLoading.value = true
  try {
    const res = await getRiskRules({ enabled_only: false })
    if (res.code === 0) {
      const rule = res.data.find((r) => r.id === Number(ruleId))
      if (rule) {
        Object.assign(formState, {
          rule_code: rule.rule_code,
          rule_name: rule.rule_name,
          rule_category: rule.rule_category,
          rule_type: rule.rule_type,
          rule_config_json: null,
          priority: rule.priority,
          risk_level: rule.risk_level,
          description: rule.description,
          is_enabled: rule.is_enabled,
        })
      }
    }
  } catch {
    message.error('获取规则详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 提交表单
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isCreate.value) {
      const res = await createRiskRule({
        rule_code: formState.rule_code,
        rule_name: formState.rule_name,
        rule_category: formState.rule_category,
        rule_type: formState.rule_type,
        rule_config_json: formState.rule_config_json,
        priority: formState.priority,
        risk_level: formState.risk_level,
        description: formState.description,
      })
      if (res.code === 0) {
        message.success('规则创建成功')
        router.push('/risk-rules')
      }
    } else {
      const updateData: UpdateRuleRequest = {
        rule_name: formState.rule_name,
        rule_category: formState.rule_category,
        rule_type: formState.rule_type,
        rule_config_json: formState.rule_config_json,
        priority: formState.priority,
        risk_level: formState.risk_level,
        is_enabled: formState.is_enabled,
        description: formState.description,
      }
      const res = await updateRiskRule(Number(ruleId), updateData)
      if (res.code === 0) {
        message.success('规则保存成功')
        router.push('/risk-rules')
      }
    }
  } catch {
    message.error('操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped lang="less">
.rule-edit-page {
  .form-card {
    max-width: 900px;
  }
}
</style>